"""
fetch_new_article.py
====================
Fetch a specific URL and ingest it as a NEW article into the system.
Useful for missing articles that were not crawled.

Usage:
    python3 src/scripts/fetch_new_article.py --url "http://..."
"""

import sys
import os
import json
import time
import re
import argparse
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, os.getcwd()) # Add CWD just in case

# Delayed imports to avoid circular deps or path issues
# from src.rag.article_cleaner import clean_article_html
# from src.core.vector_store import VectorStore

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FETCH_TIMEOUT = 10

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def extract_id_from_url(url: str) -> str:
    # Extract ID from Joomla URL (e.g. id=677)
    m = re.search(r"[?&]id=(\d+)", url)
    if m:
        return m.group(1)
    # Fallback: hash of URL
    return hashlib.md5(url.encode()).hexdigest()[:8]

def fetch_url(url: str) -> tuple[str | None, str]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (SMC-Manual-Fetch/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="ignore"), ""
    except Exception as e:
        return None, str(e)

def get_title_from_html(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return "Untitled Article"

def main():
    parser = argparse.ArgumentParser(description="Fetch and ingest a new article")
    parser.add_argument("--url", required=True, help="Target URL")
    args = parser.parse_args()
    
    # Imports inside main to ensure sys.path is ready
    from src.rag.article_cleaner import clean_article_html
    from src.vectorstore.chroma import ChromaVectorStore
    
    url = args.url
    print(f"Fetching: {url}")
    
    html, err = fetch_url(url)
    if not html:
        print(f"❌ Failed to fetch: {err}")
        sys.exit(1)
        
    print(f"✅ Fetched {len(html)} chars.")
    
    # Check login wall roughly
    if "com_user&view=login" in html.lower():
        print("⚠️  Warning: This page might be a login wall.")
        
    text, links, images = clean_article_html(html, base_url=url)
    title = get_title_from_html(html)
    
    print(f"Title: {title}")
    print(f"Text Length: {len(text)}")
    
    if len(text) < 100:
        print("⚠️  Text is very short. Proceeding anyway.")
        
    # Save JSON
    art_id = extract_id_from_url(url)
    filename = f"manual_ingest_{art_id}.json"
    filepath = PROCESSED_DIR / filename
    
    data = {
        "title": title,
        "text": text,
        "url": url,
        "source": url,
        "links": links,
        "images": images,
        "content_hash": compute_hash(text),
        "processed_at": time.time(),
        "ingest_method": "manual_script"
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Saved to {filepath}")
    
    # Embed
    print("Embedding to VectorStore...")
    try:
        # Initializing Chroma directly
        vs = ChromaVectorStore(persist_dir="data/vectorstore")
        
        # Remove old if exists (by URL)
        vs.delete_by_url(url)
        
        chunk_size = 800
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            meta = {
                "url": url,
                "title": title,
                "chunk": i,
                "source": str(filepath)
            }
            vs.add_document(chunk, meta)
            
        print(f"✅ Added {len(chunks)} chunks to VectorStore.")
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        
if __name__ == "__main__":
    main()
