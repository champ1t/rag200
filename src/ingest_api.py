import json
import requests
import time
from pathlib import Path
import hashlib
import re
import os
import sys

def detect_category(title: str, content: str) -> str:
    """
    Detect category: CONTACT, TECHNICAL_COMMAND, GENERAL_KNOWLEDGE.
    """
    title_lower = title.lower()
    content_lower = content.lower()
    
    # CONTACT
    dir_kw = ["เบอร์", "ติดต่อ", "โทร", "directory", "contact", "phone", "งาน", "ส่วน", "ฝ่าย", "รายชื่อ"]
    if any(k in title_lower for k in dir_kw):
        return "CONTACT"
    
    # TECHNICAL_COMMAND
    tech_kw = ["config", "manual", "zte", "huawei", "olt", "onu", "vlan", "pppoe", "command", "คู่มือ", "show ", "display ", "undo ", "ping "]
    if any(k in title_lower or k in content_lower for k in tech_kw):
        return "TECHNICAL_COMMAND"
        
    return "GENERAL_KNOWLEDGE"

def clean_and_format_markdown(title: str, raw_content: str) -> str:
    """
    1. Smart Spacing (Fix "Chumphon077" -> "Chumphon 077")
    2. Clean noise
    3. Markdown formatting
    """
    # [SMART FIX] Insert space ONLY between Thai characters and digits
    # This fixes: "ชุมพร0" -> "ชุมพร 0" but keeps "0-7750" intact.
    processed = re.sub(r'([\u0e00-\u0e7f])(\d)', r'\1 \2', raw_content)
    
    # Simple formatting if not HTML
    if "<" not in processed or ">" not in processed:
        # It's likely plain text from the new React API
        text = processed.strip()
    else:
        # Still HTML? Use BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(processed, "lxml")
            for unwanted in soup(["nav", "aside", "header", "footer"]):
                unwanted.decompose()
                
            # [CRITICAL FIX] Convert <img> to Markdown so get_text() doesn't erase them
            for img in soup.find_all("img"):
                img_src = img.get("src", "")
                if img_src:
                    img_alt = img.get("alt", "รูปภาพประกอบ")
                    # Replace the image node with a text node containing the markdown
                    img.replace_with(f"\n\n![{img_alt}]({img_src})\n\n")

            # Force block elements to have newlines, so we don't need separator="\n" which breaks inline elements
            for tag in soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
                tag.insert_after("\n")
            for br in soup.find_all('br'):
                br.replace_with("\n")

            text = soup.get_text(separator=" ").strip()
        except ImportError:
            text = processed
            
    # Remove junk
    text = re.sub(r'(Today|Yesterday|All days)\s*\|\s*\d+', '', text, flags=re.I)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    lines = text.split('\n')
    md_lines = [f"# {title}\n"]
    
    in_code_block = False
    cmd_prefixes = ("show ", "display ", "undo ", "conf t", "interface ", "ip route ", "ping ", "save", "reset ", "telnet ", "ssh ")
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            if in_code_block:
                md_lines.append("```\n")
                in_code_block = False
            md_lines.append("")
            continue
            
        is_cmd = line_strip.lower().startswith(cmd_prefixes) or re.search(r'[xX]/[xX]/[xX]', line_strip)
        
        if is_cmd:
            if not in_code_block:
                md_lines.append("```")
                in_code_block = True
            md_lines.append(line_strip)
        else:
            if in_code_block:
                md_lines.append("```")
                in_code_block = False
            
            # Simple header heuristic
            if len(line_strip) < 60 and not any(c.isdigit() for c in line_strip) and not "|" in line_strip:
                 md_lines.append(f"## {line_strip}")
            else:
                 md_lines.append(line_strip)
                 
    if in_code_block:
        md_lines.append("```")
        
    return "\n".join(md_lines)

def sanitize_filename(title: str) -> str:
    clean_title = re.sub(r'[^\w\u0e00-\u0e7f]+', '_', title).strip('_')
    return f"{clean_title}.json"[:100]

def ingest_km_api(api_url: str, frontend_url: str, out_dir: str):
    print(f"[API] FETCHING: {api_url}")
    try:
        r = requests.get(api_url, timeout=20)
        r.raise_for_status()
        items = r.json()
        # If it's a single item (as seen in my probe), wrap in list
        if isinstance(items, dict):
            items = [items]
        print(f"[API] FOUND: {len(items)} items")
    except Exception as e:
        print(f"[API] ERROR: {e}")
        return

    out_path_base = Path(out_dir)
    count = 0
    for item in items:
        # Support both 'id' and 'id' as field
        doc_id = item.get("id") or count
        title = item.get("title", f"Article {doc_id}")
        raw_content = item.get("content", "") or item.get("text", "") # Support 'text' field too
        
        category = detect_category(title, raw_content)
        category_dir = out_path_base / category
        category_dir.mkdir(parents=True, exist_ok=True)

        url = f"{frontend_url.rstrip('/')}/?id={doc_id}"
        clean_markdown = clean_and_format_markdown(title, raw_content)
        
        # Pull links
        links = []
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        for m in re.finditer(url_pattern, clean_markdown):
            links.append({"text": "Link", "href": m.group()})

        doc = {
            "url": url,
            "title": title,
            "text": clean_markdown,
            "links": links,
            "content_hash": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
            "processed_at": time.time(),
            "content_type": "api_import",
            "category": category
        }
        
        filename = sanitize_filename(title)
        with open(category_dir / filename, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        
        print(f"[API] [{category}] SAVED: {title} -> {filename}")
        count += 1

    print(f"[API] FINISHED: {count} docs processed.")

if __name__ == "__main__":
    API_URL = "http://10.192.133.200:5174/api/knowledge"
    FRONTEND_URL = "http://10.192.133.200:5173/"
    OUT_DIR = "data/processed"
    
    ingest_km_api(API_URL, FRONTEND_URL, OUT_DIR)
