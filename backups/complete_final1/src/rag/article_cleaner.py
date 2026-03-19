"""
Article Content Cleaner
Removes UI noise and truncates article content for faster LLM processing.
Includes Fast-Path V2 for structured content and IP tables.
Includes Phase 20.5: Navigation Filter & Topic-Anchored Extraction.
"""
import re
from typing import Tuple, List, Dict

from src.ingest.clean import clean_html_to_text  # Optional if used locally

# HTML Parsing (Fix A)
try:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False # Fallback?


# Noise patterns to remove
NOISE_PATTERNS = [
    r"mod_vvisit_counter.*?(?=\n\n|\Z)",  # Visitor counter blocks
    r"ผู้เข้าชม.*?ครั้ง",  # Visitor count text
    r"พิมพ์.*?อีเมล",  # Print/Email buttons
    r"แชร์.*?Facebook",  # Social share buttons
    r"ลิงก์ที่เกี่ยวข้อง.*?(?=\n\n|\Z)",  # Related links section
    r"เขียนโดย.*?(?=\n)",  # Author metadata (keep minimal)
    r"แก้ไขล่าสุด.*?(?=\n)",  # Last modified metadata
    r"js_jamba.*?(?=\n)",  # Template artifacts
    r"Joomla.*?(?=\n)",  # Joomla references
    r"Joomlashack.*?(?=\n)",  # Joomlashack template
    r"Template.*?by.*?(?=\n)",  # Template attribution
    r"Designed by.*?(?=\n)",  # Design attribution
    r"วัน.*?เวลา.*?น\.(?=\n)",  # Date/time stamps (if not in main content)
    # Phase 45: Specific Sidebar/Menu Noise
    r"Convert ASR920.*?(?=\n)",
    r"Get IP IPPhone.*?(?=\n)",
    r"ตรวจสอบ Version.*?(?=\n)",
    r"คู่มือการใช้งาน.*?(?=\n)",
    r"ระบบงานภายใน.*?(?=\n)",
    r"ผส\.บลตน\..*?(?=\n)",
    r"ผจ\.สบลตน\..*?(?=\n)",
    r"บุคลากร.*?(?=\n)",
    r"Edocument.*?(?=\n)",
    r"NT Academy.*?(?=\n)",
    r"Intranet.*?(?=\n)",
    r"Web HR.*?(?=\n)",
    r"Mail.*?(?=\n)",
    # Phase 105: Widget/Counter Noise
    r"Today\s*\|",
    r"Yesterday\s*\|",
    r"This week\s*\|",
    r"Last week\s*\|",
    r"We have:\s*\d+\s*guests",
    r"Your IP:\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    r"Visitors? Counter.*?(?=\n)",
    # Phase 174: Expanded Garbage Filters
    r"WDM\s*\(แนะนำIE\).*?(?=\n)",
    r"Time\s*:\s*\d{2}:\d{2}:\d{2}",
    r"Date\s*:\s*\d{2}/\d{2}/\d{4}",
    r"Your IP:\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    r"SMC AI.*?(?=\n)",
    r"Extension Dashboard.*?(?=\n)",
    r"System Status.*?(?=\n)",
    r"(Username|Password|Remember Me|Login|Lost Password).*?(?=\n)",
    r"ชื่อผู้ใช้.*?รหัสผ่าน.*?(?=\n)",
    r"จำข้อมูลการเข้าสู่ระบบ.*?(?=\n)",
    r"Main Menu.*?(?=\n)",
    # Phase 182: Specific Noise Removal (User Request)
    r"ศูนย์ปฏิบัติการ.*?(?=\n)",
    r"Service Management Center\(SMC\).*?(?=\n)",
    r"ผู้ดูแลระบบ.*?(?=\n)",
    r"กองทุนสำรองฯ.*?(?=\n)",
    r"แผนก.*?(?=\n)", # Generic department headers often found in footers
    # Phase 221: User-Reported Footer Noise (Team NT1 / ONT Password)
    r"เบอร์หน่วยงานต่างๆ.*?(?=\n\n|\Z)", 
    r"ศูนย์ สลภก\.3.*?(?=\n\n|\Z)",
    r"Link ที่เกี่ยวข้อง.*?(?=\n\n|\Z)",
    r"ลิงค์ภายใต้ ภก\.3.*?(?=\n\n|\Z)",
    r"Project ปรับปรุงตรวจแก้คืนดี.*?(?=\n\n|\Z)",
    r"Joomla 1\.5 Templates.*?(?=\n\n|\Z)",
    r"E-.*?SMC.*?(?=\n\n|\Z)",
]


# Navigation / Menu labels that indicate non-content lines
NAV_LABELS = [
    "หน้าหลัก", "ลงทะเบียน", "ลืมรหัสผ่าน", "ข่าวสาร SMC", "ความรู้", 
    "Template", "Wrapper", "User Menu", "Main Menu", "Login Form",
    "Joomla", "Extensions", "Content"
]

# Telemetry
import logging
logger = logging.getLogger(__name__)

def clean_article_content(content: str, keep_metadata: bool = False) -> str:
    """
    Remove UI noise from article content.
    
    Args:
        content: Raw article text
        keep_metadata: If True, keep author/date metadata
        
    Returns:
        Cleaned content
    """
    cleaned = content
    
    # Phase 185: Remove Visitor Stats Blocks (User Request)
    # Pattern: "| This month | 123 |" or "| 123 | 456 |"
    # Logic: Remove blocks containing "This month" or "Last month" with pipe delimiters
    # Or just remove lines that look like a pipe-stats table generally if they appear in header/footer
    
    # Phase 185 (v2): Brute Force Line Cleaning (Regex is too fragile)
    lines = cleaned.splitlines()
    out_lines = []
    
    stats_keywords = ["Today", "Yesterday", "This week", "Last week", "This month", "Last month", "All days", "Visitor", "Your IP"]
    
    for line in lines:
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
            
        # 1. Kill single-column stats | 61 | 522 ...
        # If line consists ONLY of pipes, digits, and whitespace
        if re.match(r'^[\s\|\d]+$', s):
            continue
            
        # 2. Kill Table-Row Views (Joomla repeated headers)
        # e.g. | add adsl Huawei | ...
        if s.startswith('|') and len(s) > 5:
             # If it starts with pipe, likely a table row
             # If it has > 3 pipes, definitely a table row
             if s.count('|') > 3: continue
             
        # 3. Kill Footer Stats
        if any(k in s for k in stats_keywords) and (len(s) < 100 or "|" in s):
             continue
             
        out_lines.append(line)
    
    cleaned = "\n".join(out_lines)

    # Remove noise patterns
    for pattern in NOISE_PATTERNS:
        # Skip author/date patterns if keep_metadata=True
        if keep_metadata and ("เขียนโดย" in pattern or "แก้ไข" in pattern or "วัน" in pattern):
            continue
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def is_navigation_dominated(content: str) -> bool:
    """
    Check if content appears to be primarily a navigation menu or directory list.
    (Phase 20.5)
    """
    if not content:
        return True

    # Phase 221 Fix: Strip navigation/footer noise BEFORE checking density
    # This prevents the footer links from skewing the "is navigation" check
    # and ensures we don't treat a valid article as a nav page just because of a long footer.
    # We use a lightweight local strip to avoid circular imports if possible, 
    # but strip_navigation_text is in this same file, so we can use it (or similar logic).
    
    # Let's just strip the footer markers we know about
    content_lower = content.lower()
    cutoff_markers = ["link ที่เกี่ยวข้อง", "เบอร์หน่วยงานต่างๆ", "เลือกหัวข้อที่เกี่ยวข้อง", "หัวข้อที่เกี่ยวข้อง", "ลิงค์ภายใต้"]
    for marker in cutoff_markers:
        if marker in content_lower:
            # Find the marker position (case insensitive)
            idx = content_lower.find(marker)
            # Only cut if it's in the lower half (to be safe? or just cut?)
            # The strip_navigation_text logic uses "last 30% or if file is small".
            # Here we just want to remove obvious footer junk for the CHECK.
            if idx > len(content) * 0.3: 
                content = content[:idx].strip()
                break

    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if not lines:
        return True
        
    total_lines = len(lines)
    nav_lines = 0
    short_lines = 0
    
    # Logic fix: Original is_navigation_dominated was cut off.
    # Re-implementing logic here correctly.
    
    for line in lines:
        is_nav = any(label in line for label in NAV_LABELS)
        if is_nav:
            nav_lines += 1
            
        if len(line.strip()) < 40 and not is_nav:
             short_lines += 1
             
    # Phase 175: Protection for Long How-to Articles (User Request)
    # Rule 1: IF text_length > 500 AND (has_numbered_list OR has_howto_keywords) -> NOT Navigation
    # Phase 183 Fix: Relax length check to > 300 if intent is strong (EDIMAX Case)
    
    has_numbered = re.search(r'^\s*\d+[\.)]', content, re.MULTILINE)
    has_howto = any(k in content for k in ["วิธี", "ขั้นตอน", "การตั้งค่า", "step", "setup", "config"])
    
    if len(content) > 300 and (has_numbered or has_howto):
         return False

    if len(content) > 500 and (has_numbered or has_howto): # Old rule check redundant but safe
        return False

    # Rule 2: IF paragraph_count >= 2 (Paragraph = block of text > 80 chars) -> NOT Navigation
    paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 80]
    if len(paragraphs) >= 2:
        return False

    # Heuristic: If > 50% lines are explicit nav labels
    if total_lines > 0 and nav_lines / total_lines > 0.5:
        return True
        
    # Heuristic: If we have many short lines AND some nav labels
    if total_lines > 0 and (short_lines / total_lines > 0.6) and nav_lines > 2:
        return True
        
    return False

# Phase 47: Comprehensive Sidebar/Menu items (from User Request)
SIDEBAR_ITEMS = [
    "ตรวจสอบ ONU Event Log",
    "NMS",
    "ศูนย์ปฏิบัติการระบบสื่อสารข้อมูล",
    "NT Academy",
    "Intranet NT",
    "E-Mail NT",
    "Web HR",
    "Edocument",
    "ลืมชื่อเข้าใช้งาน?",
    "Convert ASR920",
    "Get IP IPPhone",
    "Systems Monitoring Center"
]

def strip_menus(content: str) -> str:
    """
    Heuristically strip repeated menu blocks.
    Refactored to remove BLOCKS of menu items anywhere in the text, 
    rather than truncating the rest of the file (which kills content if sidebar is at top).
    """
    lines = content.split('\n')
    cleaned_lines = []
    
    # Buffer for potential menu lines
    # We only drop them if we hit a sequence of >= 3
    menu_buffer = []
    
    for line in lines:
        line_s = line.strip()
        if not line_s:
            # Empty lines? Treat as neutral. 
            # If we are buffering menus, empty line usually continues the menu block visual
            # But if we flush, we flush.
            if menu_buffer:
                menu_buffer.append(line)
            else:
                cleaned_lines.append(line)
            continue
            
        # Check against NAV_LABELS or SIDEBAR_ITEMS
        is_menu = any(m in line_s for m in NAV_LABELS) or \
                  any(s in line_s for s in SIDEBAR_ITEMS)
                  
        if is_menu:
            menu_buffer.append(line)
        else:
            # Hit a non-menu line.
            # Check buffer status
            if len(menu_buffer) >= 3:
                # Confirmed menu block (>=3 items). Drop it.
                # (Maybe keep a placeholder or just drop)
                pass 
            else:
                # Not a menu block (false positives?). Flush to output.
                cleaned_lines.extend(menu_buffer)
            
            # Clear buffer and add current valid line
            menu_buffer = []
            cleaned_lines.append(line)
            
    # Handle remaining buffer at end
    if len(menu_buffer) < 3:
        cleaned_lines.extend(menu_buffer)
    # else: dropped
        
    return "\n".join(cleaned_lines)


def mask_sensitive_data(content: str) -> str:
    """
    Mask sensitive credentials like usernames, passwords.
    (Phase 46)
    """
    masked = content
    # Regex: (password|pass|รหัสผ่าน)\s*[:=]\s*(\S+)
    patterns = [
        r"(password|pass|passwd|pwd|รหัสผ่าน|รหัส)\s*[:=]\s*(\S+)",
        r"(username|user|usr|sea\s*id|ชื่อผู้ใช้|login)\s*[:=]\s*(\S+)",
        r"(user|login)\s+([a-zA-Z0-9_\-]+)", # Match "User root" without colon
    ]
    
    for p in patterns:
        def repl(m):
            key = m.group(1)
            val = m.group(2)
            if len(val) < 2: return m.group(0)
            # Phase 136: Strict Block (No Pattern Hint)
            return f"{key}: [ข้อมูลถูกซ่อนตามนโยบายความปลอดภัย - กรุณาตรวจสอบจากต้นฉบับ]"
            
        masked = re.sub(p, repl, masked, flags=re.IGNORECASE)
    return masked



def is_metadata_dominated(content: str) -> bool:
    """
    Check if content is dominated by metadata/UI noise.
    """
    if not content:
        return True
        
    content_lower = content.lower()
    
    # Check for Joomla/template indicators
    joomla_indicators = ["joomla", "joomlashack", "template by", "designed by"]
    has_joomla = any(ind in content_lower for ind in joomla_indicators)
    
    # Check for technical content signals (Body Content)
    # Must have at least one significant signal to be considered "body"
    body_signals = [
        "http", "user", "pass", "ip", "@", "0-", "#",
        "ขั้นตอน", "วิธี", "คำสั่ง", "หมายเลข", "ติดต่อ",
        "service", "config", "manual", "guide", "command", "ping", "display"
    ]
    has_body = any(sig in content_lower for sig in body_signals)
    
    # Count metadata lines
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if not lines:
        return True
    
    metadata_count = 0
    for line in lines:
        l_lower = line.lower()
        if any(kw in l_lower for kw in ["เขียนโดย", "แก้ไข", "วัน", "เวลา", "author", "date", "modified"]):
            metadata_count += 1
        elif any(kw in l_lower for kw in joomla_indicators):
            metadata_count += 1
        elif any(kw in l_lower for kw in NAV_LABELS): # Treat nav as metadata
            metadata_count += 1
            
    metadata_ratio = metadata_count / len(lines)
    
    # Dominated if: 
    # 1. Has Joomla AND (high metadata ratio OR no strong body signals)
    # 2. Or very high metadata ratio (> 80%) regardless of Joomla
    # 3. Or absolute lack of body signals with some metadata present
    
    if has_joomla and (metadata_ratio > 0.4 or not has_body):
        return True
        
    if metadata_ratio > 0.8:
        return True
        
    if not has_body and metadata_count > 0:
        return True
        
    return False


def extract_keywords(query: str) -> List[str]:
    """
    Extract keywords from query for relevance scoring.
    """
    # Remove common words
    stop_words = {"ขอ", "แค่", "เบอร์", "รูป", "ภาพ", "ข่าว", "the", "and", "or", "ของ", "ที่", "และ", "ใน"}
    
    words = re.findall(r'\w+', query.lower())
    keywords = [w for w in words if len(w) >= 3 and w not in stop_words]
    
    return keywords


def score_paragraph_relevance(paragraph: str, keywords: List[str]) -> float:
    """
    Score paragraph relevance based on keyword overlap.
    """
    if not keywords:
        return 1.0  # If no keywords, keep all paragraphs
    
    para_lower = paragraph.lower()
    matches = sum(1 for kw in keywords if kw in para_lower)
    
    # Normalize by number of keywords (capped)
    # If we check 5 keywords, matching 1 is good (0.2), matching 5 is great (1.0)
    score = matches / max(len(keywords), 1)
    
    # Boost for Technical Entities (always relevant)
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', paragraph): score += 0.3  # IP
    if re.search(r'https?://', paragraph): score += 0.2  # URL
    if re.search(r'0\d{8,9}', paragraph): score += 0.2  # Phone
    if "display" in para_lower or "ping" in para_lower: score += 0.2 # Command common words
    
    return min(score, 1.5) # Allow > 1.0 boosting


def truncate_content(content: str, query: str, max_chars: int = 3000) -> Tuple[str, bool]:
    """
    Truncate content to max_chars, keeping most relevant paragraphs.
    """
    if len(content) <= max_chars:
        return content, False
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    if not paragraphs:
        return content[:max_chars], True
    
    # Extract keywords from query
    keywords = extract_keywords(query)
    
    # Score and sort paragraphs by relevance
    scored = [(p, score_paragraph_relevance(p, keywords)) for p in paragraphs]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Select top paragraphs until we hit max_chars
    selected = []
    total_chars = 0
    
    for para, score in scored:
        if total_chars + len(para) + 2 <= max_chars:  # +2 for \n\n
            selected.append(para)
            total_chars += len(para) + 2
        else:
            break
    
    # Re-sort selected paragraphs by original order (approximate)
    # This maintains narrative flow (Warning: might effectively shuffle if we just rely on presence)
    # To do this right, we should keep original index.
    
    # Actually, let's just join them. We lost original order in the sort.
    # But RAG doesn't care much about order if paragraphs are self-contained.
    # However, for procedure steps, order MATTERS.
    
    # Let's fix ordering
    # Add index to tuple: (para, score, index)
    
    paragraphs_with_idx = []
    for i, p in enumerate(paragraphs):
         paragraphs_with_idx.append((p, score_paragraph_relevance(p, keywords), i))
         
    paragraphs_with_idx.sort(key=lambda x: x[1], reverse=True)
    
    selected_indices = []
    total_chars = 0
    for p, score, idx in paragraphs_with_idx:
        if total_chars + len(p) + 2 <= max_chars:
            selected_indices.append(idx)
            total_chars += len(p) + 2
        else:
            break
            
    selected_indices.sort()
    
    final_selected = [paragraphs[i] for i in selected_indices]
    truncated = '\n\n'.join(final_selected)
    
    return truncated, True


def has_structured_content(content: str) -> bool:
    """
    Check if content has structured enumeration or IP table patterns (Fast-Path V2).
    """
    # Phase 46: Exclude Navigation Menu
    if is_navigation_dominated(content):
        return False

    # 1. Numbered lists (Fast-Path V1)

    numbered_pattern = r'^\s*\d+[\.)]\s+.+'
    numbered_matches = re.findall(numbered_pattern, content, re.MULTILINE)
    if len(numbered_matches) >= 2:
        return True
        
    # 2. IP List/Table patterns (Fast-Path V2)
    # Look for many IP addresses
    ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    ips = re.findall(ip_pattern, content)
    if len(ips) >= 8:  # Heuristic: lots of IPs -> likely an IP table/list
        return True
        
    # Look for repeated "Key: Value" lines typical of lists
    lines = content.splitlines()
    key_value_count = 0
    for line in lines:
        if ':' in line or '\t' in line or '   ' in line:
             if any(x in line for x in ['.', '0', '1', '2']): # basic digit/dot check
                 key_value_count += 1
    
    if key_value_count >= 5 and len(ips) >= 4:
        return True

    return False


def format_fact_item(lines: List[str], enable_formatting: bool = True) -> str:
    """
    Format a fact item into readable multiline text.
    (Phase 172: Enhanced Link Splitting (FTP/HTTP))
    """
    if not lines:
        return ""
    
    # Join lines
    text = ' '.join(lines)
    
    if not enable_formatting:
         return text
    
    # Remove duplicate numbering prefix
    text = re.sub(r'^\d+[\.)]\s+', '', text)
    
    # Strip Joomla footer noise and Nav labels if they leaked in
    text = re.sub(r'Joomla.*', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'Template by.*', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'แก้ไขล่าสุด.*', '', text, flags=re.IGNORECASE).strip()
    
    # Phase 172: Advanced Link Itemization (Robust Splitting)
    if enable_formatting and (text.count("http") + text.count("ftp://") >= 1):
        # Extract pairs of Title+URL
        parts = re.split(r'((?:ftp|https?)://[^\s\)]+)', text)
        lines_out = []
        for i in range(0, len(parts) - 1, 2):
            raw_title = parts[i].strip()
            url = parts[i+1].strip()
            
            # Clean title residue (remove trailing separators and leading noise)
            title = re.sub(r'[\s\(\-\:\(\[\|]+$', '', raw_title).strip()
            title = re.sub(r'^[\s\)\],]+', '', title).strip()
            # If title is just a number or too short, or just noise, skip title
            if title and len(title) > 1:
                lines_out.append(f"{title}\n  🔗 {url}")
            else:
                lines_out.append(f"🔗 {url}")
        
        # Handle trailing text after last URL
        if len(parts) % 2 != 0 and parts[-1].strip():
             trailing = parts[-1].strip().strip(')').strip()
             if trailing:
                 if lines_out:
                      # If it looks like a new item or just noise?
                      # For safety, just append to last URL or new line
                      if len(trailing) > 20: 
                           lines_out.append(trailing)
                      else:
                           lines_out[-1] += f" {trailing}"
                 else:
                      lines_out.append(trailing)
        
        if lines_out:
            text = "\n".join(lines_out)
            return text # Early exit as we've formatted manually
    
    # Normalize numbering/bullets
    text = re.sub(r'^\s*[•\-]\s*', '', text) # Strip leading bullets from first line if join added them
    
    # Masking is handled by ArticleInterpreter, so we keep text raw here.

    # User/Pass/IP
    text = re.sub(r'([Uu]ser(?:name)?\s*[:=]\s*\S+)', r'\n   - \1', text)
    text = re.sub(r'([Pp]ass(?:word)?\s*[:=]\s*\S+)', r'\n   - \1', text)
    text = re.sub(r'\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r'\n   - IP: \1', text)
    
    # Clean up
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    
    return text


def detect_and_summarize_tables(lines: List[str], enable_formatting: bool = True) -> List[str]:
    """
    Detect contiguous table rows and summarize if too long.
    (Phase 172: Enhanced formatting for raw table data)
    """
    processed = []
    current_table = []
    
    def flush_table():
        if not current_table: return
        
        # Phase 172: Pre-format rows to handle raw pipes/whitespace
        if not enable_formatting:
            processed.extend(current_table)
            current_table.clear()
            return
        formatted_rows = []
        for row in current_table:
            # Clean: "| 51 | 123 |" -> "51, 123"
            clean_row = re.sub(r'^\s*\|\s*', '', row)
            clean_row = re.sub(r'\s*\|\s*$', '', clean_row)
            segments = [s.strip() for s in clean_row.split('|') if s.strip()]
            if segments:
                # Phase 172: Join with commas instead of pipes for cleaner non-table look
                formatted_rows.append(", ".join(segments))
            else:
                formatted_rows.append(row)

        if len(formatted_rows) > 5:
            # Keep Header + Top 3 + Summary
            summary = [formatted_rows[0]] 
            summary.extend(formatted_rows[1:4])
            summary.append(f"... (และอีก {len(formatted_rows)-4} รายการ ดูเพิ่มเติมในลิงก์ต้นฉบับ)")
            processed.extend(summary)
        else:
            processed.extend(formatted_rows)
        current_table.clear()

    for line in lines:
        # Check if line looks like a table row
        is_table_row = False
        # Relaxed pipe check: at least 1 pipe and looks like data
        if '|' in line and line.count('|') >= 1: is_table_row = True
        elif re.match(r'^\d+\s+\d{8,}\s+', line): is_table_row = True # Asset ID pattern
        elif re.match(r'^\d+\s{2,}\S+', line): is_table_row = True # Number + gap + text
        
        if is_table_row:
            current_table.append(line)
        else:
            flush_table()
            processed.append(line)
            
    flush_table()
    return processed


def _is_valid_fact(text: str, seen: set, keywords: List[str] = None, strict_seen: set = None) -> bool:
    """
    Check if a fact is valid and relevant.
    """
    if len(text) < 5: return False
    text_lower = text.lower()
    
    # Deduplication
    # 1. Substring check
    if any(text_lower in s or s in text_lower for s in seen): return False
    
    # 2. Strict normalized check (if provided)
    if strict_seen:
        norm = re.sub(r'\W+', '', text_lower)
        if norm in strict_seen: return False
    
    # Nav/Noise Filtering
    # Fix: Stop "Content" from matching "Valid Content..."
    # Only match if the line IS the label (or very close) or starts with it followed by non-text
    for nav in NAV_LABELS:
        nav = nav.lower()
        if nav not in text_lower: continue
        
        # Exact match or wrapped in weak chars
        # If line is short (< 40) AND contains nav label -> Suspicious
        if len(text) < 40:
             # Check if it's literally just the label or "Label: ..."
             if text_lower.startswith(nav) or text_lower == nav:
                 return False
                 
    # Reject generic "Title (URL)" links often found in footer
    if "http" in text_lower:
        text_no_url = re.sub(r'\(?https?://\S+\)?', '', text).strip()
        if len(text_no_url) < 5: return False # Just a link
        
        # If it looks like a menu item: "Main Menu (http...)"
        # Use token check to avoid matching "Fiberhome" as "home"
        tokens = set(re.split(r'\W+', text_lower))
        suspicious = {"menu", "home", "main", "service", "link", "back", "next"}
        if not tokens.isdisjoint(suspicious):
             # Stricter threshold: 25 chars
             if len(text_no_url) < 25: return False

    # Relevance Scoring
    if keywords:
        score = score_paragraph_relevance(text, keywords)
        if score < 0.2: 
             return False
             
    # Phase 105: Strict Domain/IP Blocklist
    # Block internal dashboards, private IPs, and generic containers if they lack context
    # 1. Private IP Ranges (192.168.x.x, 10.x.x.x) UNLESS used in a "command context" (checked by score > 0.3)
    # But user wants STRICT blocking of these specific irrelevant IPs.
    # Actually, 192.168.1.1 might be relevant for ONU setup!
    # User said: "Output must NO contain: 192.168"
    # Wait, 192.168.1.1 is standard ONU GW.
    # User said: "SMC Extension Dashboard (192.168...) ... SMC AI ... pvd login" should be cut.
    # Let's block SPECIFIC IPs or Contexts, not all 192.168.
    # But user explicit request: "URL มี 192.168. หรือ 10. (private IP ranges)" -> Block.
    # Okay, complying with strict request for Phase 105 golden case.
    
    if "192.168." in text or "10." in text:
         # Exception: If it looks like a command example?
         # User Example: "pon-onu-mng gpon-onu_1/2/7:9" -> No IP.
         # "service internet ... iphost 1 ..." -> No IP.
         # But usually gateway is 192.168.1.1.
         # If strict request is to block, we block facts containing these.
         # Re-read: "URL มี ... (private IP ranges)" -> Block LINKS/URLs, maybe not text?
         # "URL มี 192.168. หรือ 10." -> Implies blocking links with these IPs.
         pass # Handled below in Link Logic

    # 1. Blocklist Domains/Keywords
    blocklist = ["pvd.mfcfund.com", "nms", "dashboard", "smc ai", "intranet", "web hr"]
    if any(b in text_lower for b in blocklist): return False

    # 2. Block Links with Private IPs (as requested)
    # Regex for URL with private IP
    if re.search(r'https?://(?:192\.168\.|10\.)', text_lower):
         return False
    
    # 3. Block Ports
    if re.search(r':8080|:8999', text):
         return False

    return True


def is_content_safe(text: str) -> bool:
    """
    Phase 78: Strict filter for footer/menu leakage.
    Returns False if text contains forbidden phrases.
    """
    text = text.lower()
    
    # Phase 174: Deduplication Check (Simple)
    # If text is exactly "WDM (แนะนำIE)" or standard footer
    if "wdm (แนะนำie)" in text: return False
    
    # 1. Forbidden Keywords (Footer Noise)
    forbidden = [
        "ศูนย์ปฏิบัติการระบบสื่อสารข้อมูล", 
        "service management center", 
        "joomla", 
        "visitors counter",
        "pagenavigation"
    ]
    if any(k in text for k in forbidden):
        return False
        
    # 2. Forbidden URLs (Recursive Home Links)
    if "http://10.192.133.33/smc/" in text:
        return False
        
    return True


def strip_navigation_text(content: str) -> str:
    """
    Phase 124: Runtime Text Cleaner for Tutorial Mode.
    Removes blocks of text that look like navigation menus even after HTML cleaning.
    Target: Short lines, pipe-separated links, high density of nav keywords.
    """
    if not content: return ""
    
    lines = content.split('\n')
    cleaned_lines = []
    candidate_buffer = []
    
    # Threshold for "block vs content"
    # If 4+ consecutive non-bullet short lines -> treat as Menu/Sidebar
    SHORT_BLOCK_THRESHOLD = 4
    
    def flush_buffer(is_garbage: bool):
        nonlocal candidate_buffer
        if not is_garbage:
            cleaned_lines.extend(candidate_buffer)
        candidate_buffer = []

    for line in lines:
        line_strip = line.strip()
        
        # Keep empty lines (structure) but they break blocks?
        # Actually empty lines often separate menu items.
        # Treat empty lines as part of the block if we are in one?
        if not line_strip:
            # If buffer has stuff, append blank line to buffer?
            # Or just ignore blank lines for block counting?
            if candidate_buffer:
                candidate_buffer.append(line)
            else:
                cleaned_lines.append(line)
            continue
            
        # 1. Immediate Kill: Pipe Separators (Menu Bar)
        if "|" in line_strip and len(line_strip) < 100:
            pipes = line_strip.count("|")
            if pipes >= 2 or (pipes >= 1 and len(line_strip) < 50):
                # This is definitely a menu line. 
                # If we have a buffer of short lines, they might be part of this menu area?
                # Safer to flush as valid if we weren't sure, OR assume this defines the context?
                # Let's just kill this line.
                flush_buffer(len(candidate_buffer) >= SHORT_BLOCK_THRESHOLD)
                continue 

        # 2. Immediate Kill: Explicit Nav/Footer Keywords
        # Make checks robust (case insensitive)
        # 4. Footer/Copyright/Widget specific (Phase 125)
        # "เวลาส่ง", "เบอร์หน่วยงานต่างๆ", "ผู้ดูแลระบบ", "ศูนย์ปฏิบัติการ"
        noise_keywords = [
            "copyright ©", "rights reserved", "designed by", "joomla", "all rights",
            "เวลาส่ง:", "เบอร์หน่วยงานต่างๆ", "ผู้ดูแลระบบ", "ศูนย์ปฏิบัติการ",
            "visitors counter", "today :", "yesterday :",
            "link ที่เกี่ยวข้อง", "ลิงค์ภายใต้", "project ปรับปรุง",
            "เลือกหัวข้อที่เกี่ยวข้อง", "หัวข้อที่เกี่ยวข้อง"
        ]
        
        lower_line = line_strip.lower()
        if any(k in lower_line for k in noise_keywords):
            # Phase 221: Hard Stop for Footer Headers
            # If we see "Link ที่เกี่ยวข้อง" or "เบอร์หน่วยงาน", it's likely the start of the footer junk.
            # If we are in the last 30% of the file, CUT EVERYTHING AFTER.
            if any(k in lower_line for k in ["link ที่เกี่ยวข้อง", "เบอร์หน่วยงาน", "ลิงค์ภายใต้", "เลือกหัวข้อที่เกี่ยวข้อง", "หัวข้อที่เกี่ยวข้อง"]):
                 flush_buffer(False) # Flush what we have
                 break # STOP PROCESSING FILE
            
            # Otherwise just kill this line
            flush_buffer(len(candidate_buffer) >= SHORT_BLOCK_THRESHOLD)
            continue

        # 3. Check for Short Line (Candidate for Menu Item)
        # Must NOT start with bullet/number/dash
        is_bullet = line_strip[0] in ("-", "*", "•", "+", ">") or (line_strip[0].isdigit() and line_strip[1] in (".", ")"))
        is_short = len(line_strip) < 45 # Increased slightly to catch longer menu items
        
        if is_short and not is_bullet:
            candidate_buffer.append(line)
        else:
            # Hit a long line or bullet -> End of possible menu block
            # Check if buffer was a menu
            is_menu_block = len(candidate_buffer) >= SHORT_BLOCK_THRESHOLD
            flush_buffer(is_menu_block)
            cleaned_lines.append(line)
            
    # Flush remaining
    flush_buffer(len(candidate_buffer) >= SHORT_BLOCK_THRESHOLD)
        
    return "\n".join(cleaned_lines).strip()


def extract_topic_anchored_facts(content: str, topic_query: str, enable_formatting: bool = True) -> List[str]:
    """
    Extract structured facts that are RELEVANT to the query topic.
    (Phase 35: Optimized Ranking & Summarization)
    """
    
    if any(k in topic_query.lower() for k in ["ผู้บริหาร", "รายชื่อ", "manager", "executive"]):
        exec_list = extract_executive_list(content)
        if exec_list: return exec_list

    raw_facts = []
    seen = set()
    strict_seen = set()
    
    lines = content.split('\n')
    lines = detect_and_summarize_tables(lines, enable_formatting=enable_formatting)
    
    # Define keywords from query for relevance checking
    keywords = extract_keywords(topic_query) if topic_query else []
    
    # Phase 77: Pre-split compressed numbered lists (e.g., "1. A 2. B 3. C")
    expanded_lines = []
    for line in lines:
        # Check for multiple occurrences of " \d+. " or " \d+\) "
        # We look for pattern: (Start or Space) + Number + Dot/Paren + Space
        # Use regex split but keep delimiters
        # This regex looks for "space + number + dot + space"
        # We replace it with "\nNumber. " to force line break
        
        # Don't touch simple lines or IPs
        if len(line) > 20 and re.search(r'\s\d+[\.)]\s', line):
            # Split pattern: Look for " N. " where N is digit
            # But avoid IP addresses like 1.2.3.4
            
            # Regex: Space, digit(s), dot or paren, space. 
            # Negative lookbehind for digit or dot to avoid IPs?
            # Actually easier: substitute "\s(\d+[\.)])\s" with "\n\1 "
            new_line = re.sub(r'\s+(\d+[\.)])\s+', r'\n\1 ', line)
            if new_line != line:
                 expanded_lines.extend(new_line.split('\n'))
            else:
                 expanded_lines.append(line)
        else:
            expanded_lines.append(line)

    # Phase 107: Strict Deduplication & Noise Filter
    filtered_lines = []
    for line in expanded_lines:
        line = line.strip()
        if not line: continue
        
        # Split on Pipe if it looks like a merged layout row (Fix for "ONU ZTE")
        potential_sublines = [line]
        if "|" in line:
             segments = [s.strip() for s in line.split('|')]
             # Only treat as split if segments look like content (not just table borders)
             # But simple split is usually safe for "Facts" extraction unless we really need strict table structure.
             # Given this is text extraction, splitting is safer than keeping 2000 char line.
             if any(len(s) > 10 for s in segments):
                 potential_sublines = segments

        for subline in potential_sublines:
            subline = subline.strip()
            if len(subline) < 5: continue

            # 1. Table Artifacts (| | |)
            if re.match(r'^[\s\|]+$', subline): continue 
            # Phase 111: Specific Numeric Table Artifacts (| 51 | 522 | ...)
            if re.search(r'\|\s*\d+\s*\|\s*\d+', subline): continue 

            # 2. Metadata Noise (Aggressive Stripping)
            # Remove "Written by..." and Date patterns from within the line
            # This ensures that "Title WrittenBy Content" becomes "Title Content", matching the duplicate "Title Content"
            
            # Remove Author (Use \S+ for Thai names)
            subline = re.sub(r'เขียนโดย\s+\S+', '', subline)
            # Remove Date (Thai Format: วัน...ที่ 09 ... 2559 ... น.)
            # Use .*? to be safe about day names
            subline = re.sub(r'วัน.*?ที่\s+\d+\s+\S+\s+\d{4}\s+เวลา\s+\d{2}:\d{2}\s+น\.?', '', subline)
            # Remove Hits
            subline = re.sub(r'ฮิต:\s*\d+', '', subline)
            # Remove Table Borders again in case they were inline
            subline = re.sub(r'\|\s*\|', '', subline)

            subline = subline.strip()
            if len(subline) < 5: continue
            
            # Skip if line was ONLY metadata
            if any(xd in subline for xd in ["เขียนโดย", "สร้างเมื่อ", "อัพเดทล่าสุด", "ฮิต:"]):
                 if len(subline) < 100: continue

            # 3. Deduplication (Normalized + Substring)
            norm = re.sub(r'\s+', '', subline.lower())
            
            # Exact match check
            if norm in strict_seen: continue
            
            # Substring check: If this line is a substring of an already seen line
            # Increase limit for aggressive dedup (Phase 107)
            if len(norm) < 2000 and any(norm in s for s in strict_seen):
                 continue
            
            # Longer Check: If a seen line is a substring of THIS line (e.g. Header seen first, then Header+Content)
            # We should probably replace the stored one? But strict_seen is a set.
            # Ideally we want the longest version?
            # For now, let's just stick to dropping repetitions.
                 
            strict_seen.add(norm)
            
            filtered_lines.append(subline)
            
    lines = filtered_lines
    
    current_item = []
    has_numbered = False
    
    # Phase 75: Fact Splitting Logic
    def flush_current(curr, reason=""):
        if not curr: return
        item_text = format_fact_item(curr, enable_formatting=enable_formatting)
        
        # Phase 78: Strict Safety Check
        # Phase 105: Fix C - Quality Gate
        if not is_content_safe(item_text):
            return

        # Phase 105: Structure/Relevance Gate
        # 1. Pure Link Check: If fact is just a link with no context -> Skip (unless IP-like)
        if "http" in item_text and " " not in item_text.strip():
             # Strict: Single word URL -> Dump
             return
             
        # 2. Tech/Keyword Check (Optional Strict Mode)
        # For now, relying on _is_valid_fact and score_paragraph_relevance
        
        if _is_valid_fact(item_text, seen, keywords, strict_seen):
            raw_facts.append(item_text)
            seen.add(item_text.lower())
            strict_seen.add(re.sub(r'\W+', '', item_text.lower()))
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if any(nav == line for nav in NAV_LABELS): continue
        if any(kw in line.lower() for kw in ["joomla", "joomlashack"]): continue

        # 1. Explicit Numbering or Bullet points (- )
        match = re.match(r'^\s*(\d+)[\.)]\s+(.+)|^\s*-\s+(.+)', line)
        if match:
            has_numbered = True
            flush_current(current_item, "numbering")
            # Group 2 is for numbered, Group 3 is for bullets
            content_part = match.group(2) or match.group(3)
            current_item = [content_part] 
            continue

        # 2. Implicit Boundaries (Phase 75 + 77)
        # Check if line looks like a standalone list item (URL, Heading)
        is_url_line = "http" in line or "ftp://" in line
        is_heading = (len(line) < 60) and any(kw in line for kw in ["Manual", "คู่มือ", "Guide"]) and not is_url_line
        
        # Check Length of current item
        current_len = sum(len(l) for l in current_item)
        
        should_split = False
        if current_item:
             # Phase 77: Stricter URL Splitting
             # If line HAS URL -> It's a Fact Boundary unless previous line was short Title
             # If previous item ended with URL -> Definitely split?
             
             has_prev_url = any("http" in l or "ftp://" in l for l in current_item)
             
             if is_url_line:
                 # If previous item has URL -> Split (List of links)
                 if has_prev_url:
                     should_split = True
                 # If previous item is long (> 50 chars) -> Split (Unrelated text)
                 elif current_len > 50:
                     should_split = True
                     
             elif is_heading:
                 should_split = True
             elif current_len > 300: # Phase 77: Cap at 300 chars
                 should_split = True
        
        if should_split:
            flush_current(current_item, "boundary")
            current_item = [line]
        else:
            if current_item:
                current_item.append(line)
            else:
                 # If we haven't started numbering yet, treat as potential item
                 # If we are in "numbered mode" but this line isn't numbered?
                 # It might be continuation.
                 current_item = [line]
              
    flush_current(current_item, "end")

    # Fallback for non-numbered content (unchanged logic, just skip if raw_facts populated)
    # Actually, if we found numbered items, we usually skip fallback. 
    # But new logic populates raw_facts even for implicit splits.
    
    if not has_numbered and not raw_facts:
        for line in lines:
            # ... existing fallback logic ...
            pass # (Simplified for replacement, assuming fallback logic is below or we just use raw_facts)
    
    # Existing Fallback Logic (Re-implemented carefully to match original structure)
    if not has_numbered and not raw_facts:
         # Copy of original fallback logic
         for line in lines:
            line = line.strip()
            if not line: continue
            if any(kw in line.lower() for kw in ["joomla", "template by", "designed by"]): continue
            if is_navigation_dominated(line): continue 
            
            is_data = False
            if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line): is_data = True
            elif re.search(r'0\d{8,9}', line): is_data = True
            elif re.search(r'(user|pass|login|command|ping|display)', line.lower()): is_data = True
            elif '|' in line: is_data = True 
            elif ':' in line: is_data = True
            elif re.match(r'^\d+\s+\d{8,}', line): is_data = True
            
            if is_data:
                item_text = format_fact_item([line])
                if _is_valid_fact(item_text, seen, keywords, strict_seen):
                     raw_facts.append(item_text)
                     seen.add(item_text.lower())
                     strict_seen.add(re.sub(r'\W+', '', item_text.lower()))

    scored_facts = []
    for f in raw_facts:
        score = score_paragraph_relevance(f, keywords)
        scored_facts.append((f, score))
        
    scored_facts.sort(key=lambda x: x[1], reverse=True)
    # Phase 75: Relax limit for Directory pages? 
    # If we split finely, we might have 20 facts. 8 might be too few.
    # But Interpreter truncates anyway? 
    # Let's keep 8 high qual facts.
    final_facts = [f for f, s in scored_facts[:12]] # Increased to 12
    
    return final_facts
    
    
# Backward compatibility alias
extract_structured_facts = lambda c: extract_topic_anchored_facts(c, "")


def extract_executive_list(content: str) -> List[str]:
    """
    Extract list of executives (Name + Role) from content.
    (Phase 30: Executive List Extraction)
    """
    lines = content.split('\n')
    executives = []
    seen = set()
    
    # regex for Thai names with titles
    name_pattern = r'(?:นาย|นาง|น\.ส\.|คุณ|ดร\.|พล\.?\s?[อต]\.?)\s+[\u0E00-\u0E7F]+\s+[\u0E00-\u0E7F]+'
    # regex for roles (start of line or after name)
    role_pattern = r'(?:ผจก|ผส\.|ผจ\.|ชจญ\.|รอง\s?ผจก|หน\.|หัวหน้า|ผู้อำนวยการ|ผู้จัดการ)'
    
    for line in lines:
        line = line.strip()
        if not line or len(line) > 200: continue # Skip long paragraphs
        
        # Skip noise
        if any(kw in line.lower() for kw in ["login", "welcome", "ยินดีต้อนรับ", "เข้าสู่ระบบ", "user", "password"]): continue
        
        has_name = re.search(name_pattern, line)
        has_role = re.search(role_pattern, line)
        
        if has_name or has_role:
            # Struct Filter: Reject known wrapper links that pretend to be people (e.g. "ผจ.สบลตน." linked to com_content)
            if "Itemid=" in line or "com_wrapper" in line or "view=category" in line:
                 continue
                 
            # Sanitize Emails
            # If email is obfuscated "document.write", hide it
            if "document.write" in line or "addy" in line:
                 line = re.sub(r'[\w\.-]+@[\w\.-]+', '(Hidden Email)', line) # Placeholder replacement if simple regex matches, otherwise just clean text
                 line = re.sub(r'<script.*?</script>', '', line)
                 line = re.sub(r'document\.write.*?;', '(Email Hidden)', line)

            # Clean up
            cleaned = format_fact_item([line])
            
            # Final Safety Check: Must look like a name or role
            if len(cleaned) < 5: continue
            
            if _is_valid_fact(cleaned, seen):
                executives.append(cleaned)
                seen.add(cleaned.lower())
                
    return executives


def second_chance_procedural_extraction(content: str) -> str:
    """
    Attempt to extract procedural content even if page is noisy/nav-dominated.
    (Phase 30: Second-Chance Selection)
    """
    lines = content.split('\n')
    selected = []
    
    # Keywords that indicate procedure/action
    proc_kws = ["ขั้นตอน", "วิธี", "การจัดทำ", "รายงาน", "แบบฟอร์ม", "ส่ง", "mail", "ดาวน์โหลด", "download", "กรอก", "ระบุ", "ภายใน"]
    

    for line in lines:
        line = line.strip()
        if len(line) < 10: continue
        
        # Check for procedure keywords
        if any(kw in line.lower() for kw in proc_kws):
             if not is_navigation_dominated(line): # Ensure the line itself isn't just a menu link
                 selected.append(line)
                 
    return "\n".join(selected)


# =========================================================
# Fix A & B: DOM-Based Extraction (Centralized)
# =========================================================
def clean_article_html(html: str, base_url: str = "") -> Tuple[str, List[Dict], List[Dict]]:
    """
    Extract main content using DOM selectors (BeautifulSoup).
    Strips Navigation, Footer, Sidebars.
    Returns: (text, links, images)
    """
    if not HAS_BS4:
        return clean_article_content(html), [], []

    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Remove Global Noise (Fix B - Pruning)
    # Strip known non-content regions
    noise_selectors = [
        "nav", "header", "footer", "aside", 
        ".menubar", "#header-wrap", "#leftcol", "#rightcol", 
        ".module", ".moduleS1", ".moduleS2", "#gkMenuWrap",
        ".moduletable", ".mod_vvisit_counter", ".stats-module",
        "div[id*='counter']", "div[class*='counter']",
        "script", "style", "noscript", "iframe", "form"
    ]
    for tag in soup.select(", ".join(noise_selectors)):
        tag.decompose()
        
    # Step 0.5: Prune specific text patterns (Counters, IP Widget)
    # Be careful not to delete body text. Focus on small containers.
    # Phase 117: Enhanced Blocklist
    widget_patterns = re.compile(r"(Today\s*\||Yesterday\s*\||This\s*week|Visitors\s*Counter|Your\s*IP\s*::|แขกรับเชิญ|guests\s*online|We\s*have:\s*\d+)", re.IGNORECASE)
    for tag in soup.find_all(text=widget_patterns):
        parent = tag.parent
        if parent and parent.name in ['div', 'span', 'p', 'td']:
            if len(parent.get_text(strip=True)) < 200: 
                parent.decompose()
            else:
                 tag.extract()

    # 2. Select Main Body (Fix A - Selectors)
    # Targeted selectors for Joomla / Standard CMS
    BODY_SELECTORS = [
        "div[itemprop='articleBody']",
        "div.com-content-article__body",
        "div.article-content",
        "div.item-page",            
        "div.main-both",             # Fallback
        "table.contentpaneopen",
        "div#content",       
        "div#main-content",       
        "article"                   
    ]
    
    selected_body = None
    selector_used = "None"
    
    # Phase 117: Priority Fallback (Do not aggregate)
    for selector in BODY_SELECTORS:
        matches = soup.select(selector)
        if matches:
            # Found a high-priority match. Use it and STOP.
            # Create a clean wrapper
            selector_used = selector
            new_div = soup.new_tag("div")
            
            has_content = False
            for m in matches:
                 if len(m.get_text(strip=True)) > 20:
                     new_div.append(m)
                     has_content = True
            
            if has_content:
                selected_body = new_div
                break # STOP checking other selectors
    
    if not selected_body:
        # Fallback to body if nothing matched
        selected_body = soup.body

    # 3. Extract Text & Links
    # ...
    # Phase 117: IP Masking (10.x.x.x)
    # Applied to the final text output
    text = selected_body.get_text(separator="\n", strip=True)
    
    # Mask Internal IPs (10.x.x.x is private) but KEEP localhost or others if needed? 
    # User said "IP: 10.x.x.x ต้องถูก mask"
    text = re.sub(r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}', '10.xxx.xxx.xxx (Internal IP Masked)', text)
    
    
    if selected_body:
        soup = BeautifulSoup(str(selected_body), "html.parser")
        print(f"[ArticleCleaner] Selector Used: {selector_used}")
    else:
        # Fallback: If no body selector matched, we trust the global noise stripping
        print(f"[ArticleCleaner] Selector Used: FALLBACK (Global Pruning)")
        selected_body = soup.body

    # 3. Extract Links & Text

    links = []
    seen_links = set() # Ensure this is defined
    
    # Blocklist for Links (Stage 3)
    LINK_BLOCKLIST = [
        "pvd.mfcfund.com", "dashboard", "nms", "google.com", "facebook.com", "twitter.com",
        "joomla", "templatemonster", "adobe.com", "192.168.99.", "192.168.1."
    ]

    # Extract Links
    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        text = a.get_text(strip=True)
        if raw_href and text and not raw_href.startswith("#") and not raw_href.startswith("javascript"):
            href = urljoin(base_url, raw_href) if base_url else raw_href
            
            # Filter Logic (Fix B/C - Link Directory Noise prevention)
            if any(x in raw_href.lower() for x in ["format=pdf", "print=1", "mailto", "tmpl=component"]):
                continue
            
            # Blocklist Check
            if any(b in href.lower() for b in LINK_BLOCKLIST): continue
            if any(b in text.lower() for b in LINK_BLOCKLIST): continue

            new_text = f"{text} ({href})"
            # The original code modified a.string here, but the instruction implies just collecting links.
            # Keeping the original behavior of modifying a.string for consistency with text extraction.
            a.string = new_text 
            if href and text and href not in seen_links:
                links.append({"text": text, "href": href}) # Changed 'url' to 'href' to match original structure
                seen_links.add(href)

    # Extract Images
    images = []
    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        if src and not src.startswith("data:"):
            img_url = urljoin(base_url, src) if base_url else src
            # Skip UI images
            if any(x in img_url.lower() for x in ["button", "counter", "icon", "templ", "stat"]):
                continue
                
            alt = img.get("alt", "").strip()
            title = img.get("title", "").strip()
            
            # Caption Logic
            caption = ""
            parent = img.find_parent("figure")
            if parent:
                figcaption = parent.find("figcaption")
                if figcaption: caption = figcaption.get_text(strip=True)
                
            images.append({"url": img_url, "alt": alt or title, "caption": caption})

    # Extract Text (Table Preserved)
    for table in soup.find_all("table"):
        # Fix: Skip layout tables (contentpaneopen) to allow <p> tags to break lines naturally
        if table.get("class") and "contentpaneopen" in table.get("class"):
            continue

        rows = []
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if any(cells):
                rows.append(" | ".join(cells))
        
        if rows:
            table_text = "\n".join(rows) + "\n"
            table.string = table_text

    # Explicitly handle line breaks (Fix for single-line blobs)
    for br in soup.find_all("br"):
        br.replace_with("\n")

    body_text = soup.get_text("\n", strip=True)
    
    # Phase 118: Internal Enterprise Policy - Allow IPs/Configs (No Masking)
    # We DO NOT mask 10.x.x.x anymore as it hinders technical operations.
    
    return body_text, links, images


def format_credential_structure(text: str) -> str:
    """
    Phase 119: Type A - Deterministic Credential Formatter
    Parses messy credential text into a structured Markdown list.
    Structure:
    - Context (e.g. TOT, CAT)
      - user: ...
      - password: ...
    """
    lines = text.split('\n')
    formatted_lines = []
    
    
    # Context Keywords
    ctx_keywords = ["TOT", "CAT", "3BB", "AIS", "TRUE", "ZTE", "HUAWEI", "Fiber", "Sinet", "Cin"]
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 1. Header Detection (Standalone)
        # e.g. "ONT ZTE H8102E"
        is_header = any(k in line.upper() for k in ctx_keywords)
        is_credential = ("user" in line.lower() or "pass" in line.lower() or "admin" in line.lower() or "root" in line.lower())
        
        if is_header and not is_credential:
             formatted_lines.append(f"\n- **{line}**")
             continue
             
        # 2. Mixed Header + Credential
        # e.g. "CAT user: admin password: cat"
        if is_header and is_credential:
             # Try to split context from credential
             # Pattern: (Context) (user: ...)
             # Naive split: assume context is at start
             # Find index of first credential keyword
             match = re.search(r'(user|pass|admin|root)', line, re.IGNORECASE)
             if match:
                 split_idx = match.start()
                 context_part = line[:split_idx].strip()
                 cred_part = line[split_idx:].strip()
                 
                 if len(context_part) < 20 and context_part:
                      formatted_lines.append(f"\n- **{context_part}**")
                      line = cred_part # Process the rest as credential
                 
        # 3. Credential Parsing
        if is_credential:
            # Normalize delims
            # Replace common delimiters with newlines for list item creation
            # We want: 
            #   - user: ...
            #   - password: ...
            
            # Split by key-value pairs?
            # Regex to find "key: value" or just "key value"
            # Naive: Split by spaces/commas but respect key:value
            # Actually simple split often works for simple credentials
            tokens = re.split(r'[\s,]+', line)
            for token in tokens:
                 # Clean
                 clean = re.sub(r'[\s,]+', ' ', token).strip()
                 if clean:
                      formatted_lines.append(f"  - {clean}")
    
    removed_count = len(lines) - len(formatted_lines)
    if removed_count > 5: # Only log if significant
         print(f"[METRIC] Garbage Cleaning Removed: {removed_count} lines")
         
    return "\n".join(formatted_lines)


def smart_truncate(text: str, max_length: int = 1200, footer_url: str = "") -> str:
    """
    Truncate text softly at paragraph/section boundaries.
    (Phase 173: Direct Content Preview)
    """
    if not text:
        return ""
        
    if len(text) <= max_length:
        if footer_url:
            return text + f"\n\n📌 แหล่งที่มา: {footer_url}"
        return text

    # Split by blocks (double newline is usually paragraph break)
    blocks = text.split('\n\n')
    current_text = ""
    
    for block in blocks:
        # If adding this block exceeds limit significantly (allow slight overflow for completion)
        if len(current_text) + len(block) > max_length + 200:
            # If we haven't added much yet (< 500 chars), we might be forced to cut this block.
            # But per requirements: "No cut in mid sentence".
            # If current_text is empty, we MUST take some of this block.
            if not current_text:
                # Force take first N lines of this block
                lines = block.split('\n')
                sub_text = ""
                for line in lines:
                    if len(sub_text) + len(line) > max_length:
                        break
                    sub_text += line + "\n"
                current_text = sub_text
            break
            
        current_text += block + "\n\n"
        
    final_text = current_text.strip()
    
    # Standardized Footer
    if footer_url:
        footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
        return final_text + footer
    
    return final_text


def deduplicate_paragraphs(content: str) -> str:
    """
    Phase 189: Strict line-level deduplication.
    1. Split by newlines (not just paragraphs).
    2. Strip table rows (starting with |).
    3. Strict content hashing (whitespace normalized).
    """
    if not content: return ""
    
    # 1. Split by lines
    lines = content.splitlines()
    
    seen_hashes = set()
    cleaned_lines = []
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean: 
             cleaned_lines.append("") # Preserve structure
             continue
        
        # 2. Strip Joomla Table Rows
        # If line starts with pipe and is short/digits/junk
        if line_clean.startswith('|'):
             # Case A: "| 123" or "| 123 |"
             if re.match(r'^\|[\s\|]*\d+[\s\|]*$', line_clean): continue
             # Case B: Multi-column junk
             if line_clean.count('|') > 2: continue
        
        if re.match(r'^[\s\|]+$', line_clean): continue
        
        # Heuristic for Visitor Stats (Pipe + Digits + Short)
        if len(line_clean) < 50 and line_clean.startswith('|') and any(c.isdigit() for c in line_clean):
             continue

        # User Req 2: Kill "table-row view" (e.g. | add adsl Huawei | ...)
        # Rule: Starts with | OR has > 3 pipes
        if line_clean.startswith('|'): continue
        if line_clean.count('|') > 3: continue
        
        # User Req 1: Footer/Stats Filter (Today/Yesterday/Visitor/Your IP)
        # Check against keywords
        stats_keywords = ["Today", "Yesterday", "This week", "Last week", "This month", "Last month", "All days", "Visitor", "Your IP"]
        if any(w in line_clean for w in stats_keywords) and (len(line_clean) < 100 or "|" in line_clean):
             continue

        # 3. Hash Content
        # Validate uniqueness
        # Normalize: lower, remove all whitespace
        h = re.sub(r'\s+', '', line_clean).lower()
        if len(h) < 10:
             # Very short lines (e.g. "config", "end") - Keep duplicate
             pass 
        else:
             if h in seen_hashes:
                 continue
             seen_hashes.add(h)
             
        cleaned_lines.append(line_clean)
             
    # Reassemble with newlines
    return "\n".join(cleaned_lines)


def rank_links_by_query(links_text: str, query: str, limit: int = 5) -> str:
    """
    Phase 189: Rank links by keyword overlap + Domain Whitelist/Blacklist.
    """
    if not links_text: return ""
    
    # Pre-clean: If input is raw HTML, strip tags roughly to avoid noise
    if "<html" in links_text or "<div" in links_text or "href=" in links_text:
         # Simple tag strip
         links_text = re.sub(r'<[^>]+>', ' ', links_text)
    
    # Config
    DENY_TERMS = ["joomlashack", "template", "credit", "license", "gnu"]
    BOOST_DOMAINS = ["/smc/files/", "index.php?option=", ".pdf", "manual"]
    
    candidates = []
    
    # Extract Links
    link_matches = list(re.finditer(r'(https?://[^\s\)\>]+)', links_text))
    seen_urls = set()
    
    for match in link_matches:
        url = match.group(1)
        if url in seen_urls: continue
        
        # Deny List
        if any(d in url.lower() for d in DENY_TERMS): continue
        if any(d in url.lower() for d in DENY_TERMS): continue
        
        seen_urls.add(url)
        
        # Find Title
        start = match.start()
        # Look back 400 chars (Increased to capture long titles)
        pre_text = links_text[max(0, start-400):start]
        # Find newline to isolate current line
        last_newline = pre_text.rfind('\n')
        if last_newline != -1:
             title_chunk = pre_text[last_newline+1:].strip()
        else:
             title_chunk = pre_text.strip()
             
        # Cleanup Title
        # 1. Remove trailing URL fragments if any (rare)
        # 2. Remove leading bullets/brackets
        title = re.sub(r'[\(\)\[\]🔗\-\.\:]', ' ', title_chunk).strip()
        # 3. Remove URL paths appearing in title
        title = re.sub(r'http\S+', '', title).strip()
        # 4. Remove path-like fragments
        if "/" in title:
             title = re.sub(r'^\S+/', '', title).strip()
             
        if not title or len(title) < 3: title = "Link"
        
        candidates.append({"title": title, "url": url, "score": 0, "tags": []})

    # Scoring
    keywords = [k.lower() for k in query.split() if len(k) > 2]
    if "edimax" in query.lower(): keywords.append("edimax")
    if "cisco" in query.lower(): keywords.append("cisco")
    
    for item in candidates:
        score = 0
        text_full = f"{item['title']} {item['url']}".lower()
        
        # Keyword Match
        for kw in keywords:
            if kw in text_full: score += 1.0
            
        # Extension Boost / Tags
        if ".pdf" in item['url'].lower(): 
             score += 2.0
             if "[PDF]" not in item['tags']: item['tags'].append("[PDF]")
        if "manual" in text_full:
             score += 1.0
             if "[Manual]" not in item['tags']: item['tags'].append("[Manual]")
        if "file" in text_full:
             if "[File]" not in item['tags']: item['tags'].append("[File]")
             
        # Domain Boost
        if "/smc/files/" in item['url']: score += 1.5
        
        item['score'] = score
        
    # Sort
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Format
    output_lines = []
    # Take top N
    final_list = candidates[:limit]
    
    for item in final_list:
        tags_str = ' '.join(item['tags'])
        title_clean = item['title'].replace("  ", " ")
        if tags_str:
             title_fmt = f"{tags_str} {title_clean}"
        else:
             title_fmt = title_clean
             
        output_lines.append(f"- {title_fmt}\n  🔗 {item['url']}")
        
    return "\n".join(output_lines)

        


def extract_cli_commands(text: str, min_lines: int = 4) -> str:
    """
    Phase 215: Extraction-First Command Policy.
    Scans text for CLI-like lines to prevent LLM hallucinations.
    
    Criteria:
    - Lines starting with #, >, $, %, !
    - Lines starting with common keywords: config, display, undo, system, interface, vlan, ip route
    - Indented blocks (2+ spaces) that look like config
    - Content inside code fences ```...```
    
    Returns:
    - Extracted command block string if valid lines >= min_lines.
    - None if insufficient commands found.
    """
    if not text: return None
    
    commands = []
    lines = text.splitlines()
    
    # 1. Check for Code Fences first (Strongest Signal)
    code_blocks = re.findall(r'```(.*?)```', text, re.DOTALL)
    for block in code_blocks:
        # Check if block looks like config (not just python/json)
        # Simple heuristic: if it has newlines and looks technical
        blk_lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(blk_lines) >= 2:
             commands.extend(blk_lines)
             
    if len(commands) >= min_lines:
        return "\n".join(commands)
        
    # 2. Heuristic Scan (Line-by-Line)
    cli_starters = ("#", ">", "$", "%", "!", "config", "display", "undo", "system", "interface", "vlan", "ip ", "port ", "activate", "service-port")
    
    extracted_lines = []
    
    for line in lines:
        s_line = line.strip()
        if not s_line: continue
        
        # Check explicit CLI markers
        if s_line.lower().startswith(cli_starters):
            extracted_lines.append(s_line)
            continue
            
        # Check indented technical lines
        # (Must be strictly indented and look technical)
        if line.startswith("  ") and any(k in s_line.lower() for k in ("shutdown", "description", "address", "mode", "trunk")):
             extracted_lines.append(s_line)
             
    # De-duplicate preserving order
    pass1 = []
    seen = set()
    for l in (commands + extracted_lines):
        if l not in seen:
            pass1.append(l)
            seen.add(l)
            
    if len(pass1) >= min_lines:
        return "\n".join(pass1[:15]) # Limit to top 15 lines to avoid noise
        
    return None
