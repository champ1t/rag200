from __future__ import annotations

import json
import time
import re
from pathlib import Path
from urllib.parse import urljoin

from src.ingest.clean import clean_html_to_text
from src.ingest.state import compute_hash

# ✅ เพิ่มสำหรับดึงตารางให้คงโครงสร้าง
from bs4 import BeautifulSoup
from src.rag.article_cleaner import clean_article_html


# เบอร์โทรไทยแบบขึ้นต้นด้วย 0 (มือถือ/บ้าน)
PHONE_TH_RE = re.compile(r"(?<!\d)0\d{8,9}(?!\d)")

# อีเมล
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)

# เบอร์ภายใน (ต้องมีคำบอกใบ้ ต่อ / ภายใน / ext)
EXT_HINT_RE = re.compile(
    r"(ต่อ|ภายใน|ext\.?|extension)\s*[:\-]?\s*(\d{2,5})",
    re.IGNORECASE,
)


# =========================================================
# ✅ New: Extract text with tables preserved
# =========================================================
def extract_text_with_tables(html: str, base_url: str = "") -> tuple[str, list[dict], list[dict]]:
    soup = BeautifulSoup(html, "html.parser")

    # ✅ Step A: Extract only Article Body (Systematic Fix)
    # Check for known Content/Article wrappers to strip sidebar/menu noise at source.
    # Joomla/Standard selectors:
    BODY_SELECTORS = [
        "div.item-page",            # Joomla standard
        "div.com-content-article",  # Joomla alternative
        "div#content",              # Generic ID
        "div.article-content",      # Generic Class
        "div[itemprop='articleBody']", # Schema.org
        "article"                   # HTML5
    ]
    
    selected_body = None
    for selector in BODY_SELECTORS:
        match = soup.select_one(selector)
        if match:
            # Check if this bodyCandidate isn't "empty" or just noise
            if len(match.get_text(strip=True)) > 50:
                selected_body = match
                # print(f"[DEBUG] Extracted Article Body via {selector}")
                break
                
    if selected_body:
        # Create a new soup from just the body
        # Or replace soup contents
        soup = BeautifulSoup(str(selected_body), "html.parser")

    # ลบส่วนรบกวน (Clean Scripts/Styles)
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()


    lines = []

    # ✅ Modify links to include URL in text AND collect them
    links = []
    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        text = a.get_text(strip=True)
        
        if raw_href and text and not raw_href.startswith("#") and not raw_href.startswith("javascript"):
            # Resolve absolute URL
            href = urljoin(base_url, raw_href) if base_url else raw_href
            
            # Replace link text with "Text (URL)"
            new_text = f"{text} ({href})"
            a.string = new_text
            links.append({"text": text, "href": href})

    # ✅ NEW: Extract images & OCR
    # Phase 34: OCR Integration
    try:
        from src.ingest.ocr_processor import OCRProcessor
        ocr = OCRProcessor()
    except ImportError:
        ocr = None

    images = []
    ocr_texts = []
    
    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        if src and not src.startswith("data:"):  # Skip data URLs
            # Resolve absolute URL
            img_url = urljoin(base_url, src) if base_url else src
            alt = img.get("alt", "").strip()
            title = img.get("title", "").strip()
            
            # Try to find caption (next sibling or parent figcaption)
            caption = ""
            parent = img.find_parent("figure")
            if parent:
                figcaption = parent.find("figcaption")
                if figcaption:
                    caption = figcaption.get_text(strip=True)
            
            # Perform OCR (Phase 34)
            # Warning: This slows down ingestion significantly.
            # Only do this if we are in "deep ingest" mode or for specific extensions?
            # For now, we try to download and OCR if it looks like a content image (jpg/png)
            extracted_text = ""
            if ocr and ocr.enabled and any(x in img_url.lower() for x in [".jpg", ".png", ".jpeg"]):
                try:
                    import requests
                    # Simple fetch with timeout
                    # In production, use shared session/cache
                    ir = requests.get(img_url, timeout=2)
                    if ir.ok:
                         extracted_text = ocr.process_image(ir.content)
                         if extracted_text:
                             print(f"[OCR] Extracted {len(extracted_text)} chars from {img_url}")
                             ocr_texts.append(f"[Image Content ({alt}): {extracted_text}]")
                except Exception as e:
                    pass
            
            images.append({
                "url": img_url,
                "alt": alt or title,
                "caption": caption,
                "ocr_text": extracted_text
            })
            
    # Append OCR text to main lines so it gets indexed
    if ocr_texts:
        lines.append("\n--- Image Content ---")
        lines.extend(ocr_texts)
        lines.append("---------------------\n")

    # ดึง table แบบเป็นบรรทัด (ช่วยคง label กับเบอร์)
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if cells:
                lines.append(" | ".join(cells))
        lines.append("")  # เว้นบรรทัดหลังตาราง

    # ดึง text ทั่วไป (เผื่อมีเนื้อหานอกตาราง)
    body_text = soup.get_text("\n", strip=True)

    # รวม: ให้ table มาก่อน แล้วตามด้วย body
    merged = "\n".join([*lines, "", body_text])
    return merged, links, images


def classify_content_type(url: str, title: str, text: str) -> str:
    s = f"{url}\n{title}\n{text}".lower()

    # about
    about_keys = ["เกี่ยวกับ", "ประวัติ", "วิสัยทัศน์", "พันธกิจ", "ค่านิยม", "โครงสร้างองค์กร", "about"]
    if any(k in s for k in about_keys):
        return "about"

    emails = EMAIL_RE.findall(text)
    phones_th = PHONE_TH_RE.findall(text)
    exts = EXT_HINT_RE.findall(text)

    # หน้า contact จริงมักจะ:
    # - มีอีเมล หรือ
    # - มีเบอร์ 0xxxxxxxxx อย่างน้อย 1 หรือ
    # - มีหลาย "ต่อ/ภายใน" (รายการติดต่อหน่วยงาน)
    title_url = (url + " " + title).lower()
    looks_like_contact_page = any(k in title_url for k in ["contact", "ติดต่อ", "callcenter", "โทร", "เบอร์"])

    if len(emails) >= 1:
        return "contact"
    if len(phones_th) >= 1:
        return "contact"
    if len(exts) >= 2:
        return "contact"
    if looks_like_contact_page and len(exts) >= 1:
        return "contact"

    if looks_like_contact_page and len(exts) >= 1:
        return "contact"

    # ✅ Image-Heavy Detection (New)
    # If text is very short (< 300 chars) but has images -> Likely a scanned doc/poster
    # We should flag this so RAG doesn't try to summarize empty text.
    if len(text) < 300:
        # Check if we have image references in the text (we appended them in clean_article_html as "--- Image Content ---")
        # Or check if "img" tag counts? We don't have img count here, but we pass it.
        # Actually classify_content_type receives raw text.
        # But process_raw_html_file HAS the images list.
        # Let's verify if caller passes images list? No.
        # Heuristic: Check for [Image Content] marker logic if we had it, 
        # BUT current logic relies on text length primarily.
        
        # Simple heuristic: heavily short text = "visual"
        return "visual"

    if looks_like_contact_page and len(exts) >= 1:
        return "contact"

    # ✅ Image-Heavy Detection (New)
    # If text is very short (< 300 chars) but we assume it might be an image-based announcement
    # Since we can't see 'images' list here (scope), we rely on text length for now.
    # A true 'General' article usually has > 300 chars.
    if len(text) < 300:
        return "visual"

    return "general"




def process_raw_html_file(raw_html_path: str, out_dir: str, source_url: str) -> tuple[str, str]:
    raw_path = Path(raw_html_path)
    out_path_dir = Path(out_dir)
    out_path_dir.mkdir(parents=True, exist_ok=True)

    html = raw_path.read_text(encoding="utf-8", errors="ignore")

    cleaned = clean_html_to_text(html)

    # ✅ เปลี่ยน: ใช้ text ที่ดึงจาก table แล้วคงโครงสร้าง + images
    # ✅ เปลี่ยน: ใช้ text ที่ดึงจาก table แล้วคงโครงสร้าง + images (Fix A: Centralized)
    text, links, images = clean_article_html(html, base_url=source_url)

    content_type = classify_content_type(source_url, cleaned.title, text)
    content_hash = compute_hash(text)

    payload = {
        "url": source_url,
        "title": cleaned.title,
        "text": text,  # ✅ ใช้ text ใหม่แทน cleaned.text
        "content_type": content_type,
        "content_hash": content_hash,
        "links": links, # ✅ Added links
        "images": images, # ✅ NEW: Added images
        "processed_at": time.time(),
        "raw_file": str(raw_path),
    }

    out_file = out_path_dir / (raw_path.stem + ".json")
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return str(out_file), content_hash
