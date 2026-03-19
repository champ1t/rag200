
import re
from typing import List, Dict, Optional

# Known Provinces/Regions
PROVINCES = [
    "เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แพร่", "น่าน", "พะเยา", "แม่ฮ่องสอน",
    "พิษณุโลก", "นครสวรรค์", "อุทัยธานี", "กำแพงเพชร", "ตาก", "สุโขทัย", "เพชรบูรณ์", "พิจิตร",
    "อุบลราชธานี", "นครราชสีมา", "ขอนแก่น", "อุดรธานี", "เลย", "หนองคาย", "มหาสารคาม", "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "มุกดาหาร",
    "สงขลา", "หาดใหญ่", "ภูเก็ต", "สุราษฎร์ธานี", "สุราษ", "นครศรีธรรมราช", "นศ", "ตรัง", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส", "ชุมพร", "ระนอง", "กระบี่", "พังงา", "สตูล",
    "ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "สระแก้ว",
    "นครปฐม", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครนายก", "พระนครศรีอยุธยา", "อยุธยา", "อ่างทอง", "สิงห์บุรี", "ลพบุรี", "สระบุรี", "สมุทรสงคราม", "ราชบุรี", "เพชรบุรี", "ประจวบคีรีขันธ์", "กาญจนบุรี", "สุพรรณบุรี", "กรุงเทพ", "กทม"
]

ABBREVIATIONS = {
    "สุราษ": "สุราษฎร์ธานี",
    "surat": "สุราษฎร์ธานี",
    "นศ": "นครศรีธรรมราช",
    "nst": "นครศรีธรรมราช",
    "กทม": "กรุงเทพ",
    "bkk": "กรุงเทพ",
    "bangkok": "กรุงเทพ",
    "songkhla": "สงขลา",
    "hatyai": "หาดใหญ่",
    "โคราช": "นครราชสีมา",
    "korat": "นครราชสีมา",
    "phuket": "ภูเก็ต",
    "trang": "ตรัง",
    "yala": "ยะลา",
    "ปัตตนี": "ปัตตานี", # Typo
    "9iy'": "ตรัง", # Layout Typo
    "8iy'": "ตรัง", # Layout Typo variant? "8" is "ค". "9" is "ต". 
    "i'": "ร",
    "8;k,gl": "ค", # Random? Skip rare ones. "9iy'" is specific user report.
    "s;v": "สงขลา", # s=ห, ;=ว, v=อ ... No. 
}

# Scan list includes both full names and abbreviations
SCAN_KEYS = PROVINCES + list(ABBREVIATIONS.keys())

import difflib

def fuzzy_match_province(query: str) -> Optional[str]:
    """
    Fuzzy match query against known provinces (Robustness B).
    Returns normalized province name or None.
    """
    query_lower = query.lower().strip()
    
    # 1. Check exact/alias first
    if query_lower in ABBREVIATIONS:
        return ABBREVIATIONS[query_lower]
        
    for p in PROVINCES:
        if p in query_lower:
            return p
            
    # 2. Fuzzy Match against PROVINCES
    # cleanup query: remove "จ.", "จังหวัด"
    clean_q = query_lower.replace("จังหวัด", "").replace("จ.", "").strip()
    if len(clean_q) < 2: return None
    
    matches = difflib.get_close_matches(clean_q, PROVINCES, n=1, cutoff=0.7)
    if matches:
        return matches[0]
        
    return None

def extract_location_intent(query: str) -> List[str]:
    """
    Extract requested location from query using exact and fuzzy matching.
    Returns list of location names (normalized).
    """
    query_lower = query.lower().strip()
    locations = []
    
    # 1. Exact / Scan Logic
    for key in SCAN_KEYS:
        if key in query_lower:
            # Normalize to full name if it's an abbr
            full_name = ABBREVIATIONS.get(key, key)
            if full_name not in locations:
                locations.append(full_name)
    
    # 2. If no exact match, try fuzzy on the whole query or words?
    # extract_location_intent usually runs on full sentence. Fuzzy works best on short token.
    # If Sentence has no known province, we might skip fuzzy to avoid FP.
    # Fuzzy is mostly for "Followup" where input is just "ปัตตนี".
    
    if not locations and len(query_lower) < 20:
         fuzzy = fuzzy_match_province(query_lower)
         if fuzzy:
             locations.append(fuzzy)
            
    return list(set(locations))

# Common Noise Keywords (Footer, Menu, System Text)
NOISE_KEYWORDS = [
    "joomla", "template", "แก้ไขล่าสุด", "visitors", "copyright", "สงวนลิขสิทธิ์",
    "edocument", "nt academy", "intranet", "web hr", "e-mail", "ศูนย์ปฏิบัติการ",
    "login", "reset", "forgot password", "หน้าแรก", "download", "contact us",
    "sitemap", "rss", "atom"
]

def is_valid_mapping_line(line: str) -> bool:
    """
    Check if a line contains structured mapping data (Code, Phone, Unit).
    Used by DispatchHandler and ContactHandler.
    """
    line_lower = line.lower()
    
    # 0. BLOCKLIST (Immediate Fail: Policy/Footer/Noise)
    # Checks expanded NOISE + original "Policy" keywords
    bad_keywords = ["ให้ดำเนินการ", "sms", "url", "ตัวอย่าง", "ผู้จ่ายงาน", "ข้อความ"] + NOISE_KEYWORDS
    if any(k in line_lower for k in bad_keywords):
        return False
        
    # Pattern 1: Dispatch Code (Any 5+ Alphanum followed by Colon)
    # e.g. "XBN000201:", "09891Z0300:"
    if re.search(r"[a-z0-9]{5,}.*?:", line_lower): 
        return True
    
    # Pattern 2: Phone Number (Relaxed)
    # 02-xxxxxxx, 08x-xxxxxxx, or 0xxxxxxxxx (9-10 digits starting with 0)
    # Must use word boundary or be careful not to match "01" in "2014"
    if re.search(r"\b0\d{1,2}[-]?\d{6,8}\b", line_lower):
        return True
    # Fallback for attached or non-bounded numbers? "Tel.02..." (Use stricter length check)
    if re.search(r"0\d{8,9}", line_lower):
        return True
        
    # Pattern 3: Explicit Unit Keywords (Relaxed for Generic Handlers)
    # Captures "Unit Name" lines if they look like headers
    valid_keywords = ["สื่อสาร", "ข้อมูล", "ระดับ", "งาน", "ส่วน", "กอง", "ศูนย์", "พื้นที่", "ดูแล", "รับผิดชอบ", "วงจร", "wi-net", "เกาะ", "ปกติ", "ติดตั้ง"]
    if any(k in line_lower for k in valid_keywords):
         return True
         
    # Pattern 4: Explicit "No Info" markers
    if "ไม่มี" in line_lower and ("ข้อมูล" in line_lower or "รายละเอียด" in line_lower):
        return True
         
    return False

def strip_footer_noise(text: str) -> str:
    """
    Removes common footer noise line-by-line.
    """
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        if any(k in line.lower() for k in NOISE_KEYWORDS):
            continue
        clean_lines.append(line)
    
    return "\n".join(clean_lines)
