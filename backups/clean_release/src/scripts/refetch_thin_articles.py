"""
refetch_thin_articles.py
========================
Safe, standalone script to re-fetch SMC articles that were not properly ingested
(i.e., their processed JSON has very little text).

What this script does:
  1. Find all processed/*.json with text < MIN_TEXT_LEN chars
  2. For each article, attempt to fetch the original URL (must be on LAN 10.192.133.x)
  3. Detect login walls → SKIP if required
  4. Extract clean text using the same pipeline as the main ingest
  5. Update the processed JSON in-place (backup original first)
  6. Re-embed the updated document into the Vector Store

What this script DOES NOT touch:
  - chat_engine.py, context_manager.py, any .py in src/ (except writing new data)
  - Existing good documents (only updates thin ones)
  - Vector store entries for other documents

Usage:
    cd /path/to/rag_web
    python3 src/scripts/refetch_thin_articles.py [--dry-run] [--min-text 200]

Options:
    --dry-run     : Report what would be done, but don't change anything
    --min-text N  : Articles with text < N chars are considered "thin" (default: 200)
    --url URL     : Only re-fetch a specific URL (optional)
"""

import sys
import os
import json
import time
import re
import argparse
import shutil
import hashlib
import glob
import urllib.request
import urllib.error
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BACKUP_DIR    = PROJECT_ROOT / "data" / "processed_backup_refetch"

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_MIN_TEXT = 200
FETCH_TIMEOUT    = 8   # seconds
# NOTE: Joomla embeds a login sidebar on EVERY page even when content is public.
# We must NOT flag purely on 'option=com_user' or password input existing.
# Only flag as login wall if the main article body is absent/empty AND there's a login action.
LOGIN_REDIRECT_SIGNALS = [
    "com_user&view=login",       # explicit login page URL
    "กรุณาเข้าสู่ระบบก่อน",     # Thai: "please login first"
    "คุณต้องลงชื่อเข้าใช้ก่อน", # Thai: "you must login first"
    "this content requires login",
    "access denied",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_login_wall(html: str) -> bool:
    """
    Return True only if the page is a HARD login wall (content inaccessible).
    NOT triggered by Joomla's sidebar login form on public pages.
    """
    from bs4 import BeautifulSoup
    lower = html.lower()

    # Hard redirect signals (page IS the login page)
    for signal in LOGIN_REDIRECT_SIGNALS:
        if signal in lower:
            return True

    # Check if article body exists and has real content
    soup = BeautifulSoup(html, "html.parser")
    for sel in ["div.item-page", "div.main-both", "div.com-content-article", "div#content", "article"]:
        el = soup.select_one(sel)
        if el:
            body_text = el.get_text(strip=True)
            if len(body_text) > 100:
                return False  # Content is accessible — not a login wall

    # No recognizable body with content found → likely login-gated
    return True


def fetch_url(url: str) -> tuple[str | None, str]:
    """
    Fetch URL. Returns (html_content, error_message).
    html_content is None on failure.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (SMC-RAG-Refetch/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return resp.read().decode(charset, errors="ignore"), ""
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


def extract_text_from_html(html: str, base_url: str = "") -> tuple[str, list[dict], list[dict]]:
    """
    Extract clean text + links + images from HTML.
    Mirrors the main ingest pipeline (process_one.py).
    """
    try:
        from src.rag.article_cleaner import clean_article_html
        return clean_article_html(html, base_url=base_url)
    except ImportError:
        # Fallback: basic HTML strip
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        links = [{"text": a.get_text(strip=True), "href": a["href"]}
                 for a in soup.find_all("a", href=True)
                 if a.get_text(strip=True)]
        return text, links, []


def get_title_from_html(html: str) -> str:
    """Extract <title> tag."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def find_thin_articles(min_text_len: int, target_url: str = "") -> list[dict]:
    """Return list of {path, url, current_text_len} for thin articles."""
    results = []
    for f in sorted(glob.glob(str(PROCESSED_DIR / "*.json"))):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            text = data.get("text", "")
            url  = data.get("url", data.get("source", ""))
            if target_url and url != target_url:
                continue
            if len(text) < min_text_len:
                results.append({
                    "path": f,
                    "url": url,
                    "current_text_len": len(text),
                    "data": data,
                })
        except Exception as e:
            print(f"  [WARN] Cannot read {f}: {e}")
    return results


def reembed_document(processed_json_path: str):
    """
    Re-add a single document to the Vector Store.
    Uses the existing VectorStore.add_document() API.
    """
    try:
        import json
        with open(processed_json_path, encoding="utf-8") as fp:
            doc = json.load(fp)

        # Import vector store
        from src.core.vector_store import VectorStore
        vs = VectorStore(persist_directory="data/vectorstore")

        # Delete old embedding for this URL, then add new one
        url = doc.get("url", "")
        text = doc.get("text", "")
        title = doc.get("title", "")

        if not text or not url:
            print(f"  [WARN] Empty text or URL — skipping embed.")
            return False

        print(f"  [EMBED] Re-embedding {len(text)} chars for {url[:60]}...")

        # Try to remove old entry first (best-effort)
        try:
            vs.delete_by_url(url)
            print(f"  [EMBED] Old entry removed.")
        except Exception:
            pass  # May not exist or method may differ

        # Add new entry
        chunk_size = 800
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            meta = {
                "url": url,
                "title": title,
                "chunk": i,
                "source": processed_json_path,
            }
            vs.add_document(chunk, meta)

        print(f"  [EMBED] Added {len(chunks)} chunks to vector store. ✅")
        return True

    except ImportError as e:
        print(f"  [WARN] VectorStore import failed: {e}")
        print(f"  [INFO] You may need to run: python3 src/main.py index")
        return False
    except Exception as e:
        print(f"  [ERR] Re-embed failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Re-fetch thin SMC articles from LAN")
    parser.add_argument("--dry-run",  action="store_true", help="Show what would be done")
    parser.add_argument("--min-text", type=int, default=DEFAULT_MIN_TEXT,
                        help=f"Min text length threshold (default: {DEFAULT_MIN_TEXT})")
    parser.add_argument("--url",      type=str, default="",
                        help="Re-fetch a specific URL only")
    parser.add_argument("--no-embed", action="store_true",
                        help="Skip re-embedding (just update JSON)")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    mode_label = "[DRY-RUN] " if DRY_RUN else ""

    print("=" * 65)
    print(f"  SMC Article Re-fetcher")
    print(f"  Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Min text threshold: {args.min_text} chars")
    if args.url:
        print(f"  Target URL: {args.url}")
    print("=" * 65)

    # 1. Find thin articles
    thin = find_thin_articles(args.min_text, args.url)
    if not thin:
        print(f"\n✅ No thin articles found (all have > {args.min_text} chars). Nothing to do.")
        return

    print(f"\nFound {len(thin)} thin article(s):\n")
    for item in thin:
        print(f"  [{item['current_text_len']:4d} chars] {item['url'][:75]}")

    # 2. Create backup directory
    if not DRY_RUN and thin:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n📦 Backups will be saved to: {BACKUP_DIR}")

    print()

    succeeded = []
    skipped   = []
    failed    = []

    for item in thin:
        url  = item["url"]
        path = item["path"]
        data = item["data"]

        print(f"{'─'*65}")
        print(f"  {mode_label}Processing: {url[:70]}")
        print(f"  Stored text:  {item['current_text_len']} chars")

        # 3. Fetch URL
        html, err = fetch_url(url)
        if not html:
            print(f"  ❌ FETCH FAILED: {err} → SKIP")
            failed.append((url, err))
            continue

        print(f"  ✅ Fetched: {len(html)} chars of HTML")

        # 4. Detect login wall
        if is_login_wall(html):
            print(f"  🔒 LOGIN WALL detected → SKIP")
            skipped.append((url, "login required"))
            continue

        # 5. Extract text
        text, links, images = extract_text_from_html(html, base_url=url)
        title = get_title_from_html(html) or data.get("title", "")

        print(f"  📄 Extracted: {len(text)} chars of text, {len(links)} links")

        if len(text) <= item["current_text_len"]:
            print(f"  ⚠️  Extracted text is NOT longer than current — check page structure.")
            print(f"     (May be a JS-rendered page or iFrame content — SKIP)")
            skipped.append((url, "no improvement"))
            continue

        if DRY_RUN:
            print(f"  [DRY-RUN] Would update JSON + re-embed.")
            print(f"  [DRY-RUN] Text preview:\n    {text[:250].replace(chr(10),' ')}")
            succeeded.append(url)
            continue

        # 6. Backup original
        backup_path = BACKUP_DIR / Path(path).name
        shutil.copy2(path, backup_path)
        print(f"  💾 Backup saved: {backup_path.name}")

        # 7. Update processed JSON
        new_data = dict(data)
        new_data["title"]        = title
        new_data["text"]         = text
        new_data["links"]        = links
        new_data["images"]       = images
        new_data["content_hash"] = compute_hash(text)
        new_data["processed_at"] = time.time()
        new_data["refetched_at"] = time.time()
        new_data.pop("raw_file", None)  # no raw file since we fetched live

        with open(path, "w", encoding="utf-8") as fp:
            json.dump(new_data, fp, ensure_ascii=False, indent=2)

        print(f"  ✅ Processed JSON updated: {Path(path).name}")

        # 8. Re-embed into Vector Store
        if not args.no_embed:
            reembed_document(path)
        else:
            print(f"  [SKIP EMBED] --no-embed flag set. Run manual re-index to apply.")

        succeeded.append(url)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  {'DRY-RUN ' if DRY_RUN else ''}Summary:")
    print(f"  ✅ Succeeded:  {len(succeeded)}")
    print(f"  🔒 Skipped:   {len(skipped)}")
    print(f"  ❌ Failed:    {len(failed)}")

    if skipped:
        print(f"\n  Skipped details:")
        for url, reason in skipped:
            print(f"    {url[:65]}: {reason}")
    if failed:
        print(f"\n  Failed details:")
        for url, reason in failed:
            print(f"    {url[:65]}: {reason}")

    if not DRY_RUN and succeeded:
        print(f"\n  🎉 Done! Re-start the RAG system to use updated data.")
        print(f"  (Or: the running system will use updated data on next reload)")


if __name__ == "__main__":
    main()
