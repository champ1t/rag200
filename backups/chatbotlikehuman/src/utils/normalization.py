
import re
import difflib
from typing import Optional, List


# ==========================================
# 1. Constants & Data
# ==========================================

# ==========================================
# 1. Constants & Data
# ==========================================

import json
from pathlib import Path

def load_aliases() -> dict:
    try:
        # Assuming data/aliases.json is at project root relative to execution or src
        # Better to be robust with Path
        base_path = Path(__file__).resolve().parent.parent.parent
        json_path = base_path / "data" / "aliases.json"
        
        if not json_path.exists():
             print(f"[WARN] aliases.json not found at {json_path}")
             return {}
             
        data = json.loads(json_path.read_text(encoding='utf-8'))
        return data
    except Exception as e:
        print(f"[ERR] Failed to load aliases: {e}")
        return {}

_ALIAS_DATA = load_aliases()

PROVINCE_ALIASES = _ALIAS_DATA.get("province_aliases", {})
ROLE_ALIASES = _ALIAS_DATA.get("role_aliases", {})
UNIT_ALIASES = _ALIAS_DATA.get("unit_aliases", {})
DOMAIN_ALIASES = _ALIAS_DATA.get("domain_aliases", {})

PROVINCES = [
    "เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แพร่", "น่าน", "พะเยา", "แม่ฮ่องสอน",
    "พิษณุโลก", "นครสวรรค์", "อุทัยธานี", "กำแพงเพชร", "ตาก", "สุโขทัย", "เพชรบูรณ์", "พิจิตร",
    "อุบลราชธานี", "นครราชสีมา", "ขอนแก่น", "อุดรธานี", "เลย", "หนองคาย", "มหาสารคาม", "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "มุกดาหาร",
    "สงขลา", "หาดใหญ่", "ภูเก็ต", "สุราษฎร์ธานี", "สุราษ", "นครศรีธรรมราช", "นศ", "ตรัง", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส", "ชุมพร", "ระนอง", "กระบี่", "พังงา", "สตูล",
    "ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "สระแก้ว",
    "นครปฐม", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครนายก", "พระนครศรีอยุธยา", "อยุธยา", "อ่างทอง", "สิงห์บุรี", "ลพบุรี", "สระบุรี", "สมุทรสงคราม", "ราชบุรี", "เพชรบุรี", "ประจวบคีรีขันธ์", "กาญจนบุรี", "สุพรรณบุรี", "กรุงเทพ", "กทม"
]

# ==========================================
# 2. Text Normalization
# ==========================================

def normalize_for_contact(text: str) -> str:
    """
    Phase 138: Aggressive Normalization for Contact Matching.
    - Lowercase, Strip
    - Apply Domain Aliases
    - Normalize Separators (./_ -> space)
    - Collapse Spaces
    """
    if not text: return ""
    
    # 1. Basic Clean
    text = text.lower().strip()
    
    # 2. Replace separators with space (except hyphen if we want to preserve ip-phone)
    # User said: "replace - _ / . with space -> space" BUT also "ip-phone" desired.
    # Strategy: Replace . / _ with space. Keep - for now? 
    # Or normalize all to space then map "ip phone" -> "ip-phone"?
    # Let's clean separators first.
    # 2. Replace separators with space (including - if strictly requested, but maintain ip-phone via re-normalization?)
    # User said: "replace - _ / with space"
    text = re.sub(r'[\._/-]', ' ', text)
    
    # 3. Collapse spaces (to help alias matching)
    text = re.sub(r'\s+', ' ', text)
    
    # 4. Apply Domain Aliases (Iterative or Token?)
    # Since aliases might be multi-word ("ip phone"), we should iterate.
    # Sort aliases by length desc to match longest first
    # Optimization: Only check if substring present
    # 4. Apply Domain Aliases (Iterative or Token?)
    # Since aliases might be multi-word ("ip phone"), we should iterate.
    # Sort aliases by length desc to match longest first
    # Optimization: Only check if substring present
    # 4. Apply Domain Aliases (Iterative or Token?)
    # Since aliases might be multi-word ("ip phone"), we should iterate.
    # Sort aliases by length desc to match longest first
    # Optimization: Only check if substring present
    
    # Fix Phase 139: Explicit Sort by Key Length Descending
    sorted_aliases = sorted(DOMAIN_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
    
    for k, v in sorted_aliases:
        if k in text:
            # Word boundary check? "scip phone" shouldn't match "ip phone"
            # Simple replace might be risky but DOMAIN_ALIASES are specific.
            # Let's use simple replace for now as per "hatyai" example.
            text = text.replace(k, v.lower()) # Normalize alias result to lower for consistency?
            # Phase 138 Fix: Break after first Domain Alias match to prevent recursive/duplicate replacement
            # e.g. "omc hy" -> "ศูนย์ omc หาดใหญ่" -> matches "omc หาดใหญ่" -> "ศูนย์ ศูนย์ ..."
            break 
            
    # 5. Apply Unit Aliases (omg -> omc)
    for k, v in UNIT_ALIASES.items():
        # strict token match?
        if k in text.split():
             text = text.replace(k, v.lower())
             
    # 6. Apply Province Aliases
    for k, v in PROVINCE_ALIASES.items():
        if k in text:
             text = text.replace(k, v)
             
    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    # User Request: "ip phone" = "ip-phone". 
    # If we did replace above, we have "ip-phone".
    # Check normalization of hyphens again?
    text = normalize_hyphens(text)
    
    return text

def remove_leading_combining_marks(text: str) -> str:
    """
    Removes vowels/tone marks that appear at the beginning of the string (typos).
    e.g. "๊ u-mux" -> "u-mux"
    Thai combining marks range roughly within \u0E30-\u0E4C
    """
    if not text: return ""
    # Strip leading whitespace first
    text = text.strip()
    # Remove leading Thai combining characters
    # \u0E31 (Mai Han-Akat), \u0E34-\u0E3A (Vowels), \u0E47-\u0E4E (Tones/Marks)
    text = re.sub(r'^[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E]+', '', text)
    return text.strip()

def normalize_hyphens(text: str) -> str:
    """
    Normalize various dash/hyphen characters to a standard ASCII hyphen (-).
    """
    if not text: return ""
    # En-dash, Em-dash, Minus sign, etc.
    return re.sub(r'[\u2013\u2014\u2212]', '-', text)


def insert_thai_english_spacing(text: str) -> str:
    """
    Inserts space between Thai and English/Number characters.
    e.g. "หน่วยIP" -> "หน่วย IP", "งานFTTx" -> "งาน FTTx"
    """
    if not text: return ""
    # Thai range: [\u0E00-\u0E7F]
    # English/Num: [A-Za-z0-9]
    
    # Thai followed by Eng/Num
    text = re.sub(r'([\u0E00-\u0E7F])([A-Za-z0-9])', r'\1 \2', text)
    # Eng/Num followed by Thai
    text = re.sub(r'([A-Za-z0-9])([\u0E00-\u0E7F])', r'\1 \2', text)
    return text

def strip_contact_noise(text: str) -> str:
    """
    Strips organizational noise words to reveal the core entity.
    """
    if not text: return ""
    
    # Order matters: Compounds first ("หน่วยงาน") before simple ("หน่วย")
    noise = ["หน่วยงาน", "หน่วย", "ฝ่าย", "งาน", "ทีม", "แผนก", "ส่วน", "กอง", "ศูนย์", "กลุ่ม", "สผ"]
    
    cleaned = text
    for n in noise:
        cleaned = cleaned.replace(n, " ")
        
    return re.sub(r'\s+', ' ', cleaned).strip()

def normalize_text(text: str) -> str:
    """
    Standard text normalization:
    - Lowercase
    - Strip whitespace
    - Normalize hyphens
    - Remove leading marks (typos)
    - Collapse multiple spaces
    """
    if not text: return ""
    text = remove_leading_combining_marks(text)
    text = normalize_hyphens(text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def normalize_for_matching(text: str) -> str:
    """
    Rule A: Strict Input Normalization for Matching.
    - Trim, Lowercase
    - Collapse spaces
    - Remove prefixes ("เบอร์", "โทร", etc.)
    - Remove punctuation separators (-, _, ., /, etc.)
    - Normalize Thai Digits
    """
    if not text: return ""
    s = text.strip().lower()
    
    # 6) Normalize Thai Digits (Rule A.6)
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    arabic_digits = "0123456789"
    trans_table = str.maketrans(thai_digits, arabic_digits)
    s = s.translate(trans_table)
    
    # 4) Remove Prefixes (Rule A.4)
    # Order by length desc to handle "เบอร์หน่วยงาน" before "เบอร์"
    prefixes = ["เบอร์หน่วยงาน", "เบอร์โทร", "เบอร์ของ", "ขอเบอร์", 
                "เบอร์", "เบอ", "โทรศัพท์", "โทร", "tel"]
    
    # Must loop because multiple prefixes might exist? e.g. "ขอเบอร์โทร"
    # Or just strip distinct ones.
    # Logic: iteratively remove if starts with
    changed = True
    while changed:
        changed = False
        s_check = s.strip()
        for p in prefixes:
            if s_check.startswith(p):
                s = s_check[len(p):].strip()
                changed = True
                break
    
    # 5) Remove Punctuation Separators (Rule A.5)
    # separators: - _ . / ( ) [ ] { } : ; , #
    # Rule says "ignore for matching", meaning replace with space or empty?
    # "IP-Phone-helpdesk" == "ip phone helpdesk" -> Space replacement seems safest for tokenization
    # But "ipphonehelpdesk" is also implied by "ignore".
    # User Example: "IP-Phone-helpdesk" == "ip phone helpdesk" == "ipphonehelpdesk"
    # To support ALL variations, we usually normalize to "no space, no punct" (key_norm)
    # AND "spaced tokens" (tokens).
    
    # Here, we normalize to a "clean spaced string" first.
    s = re.sub(r"[\-_\./\(\)\[\]\{\}:;,#]", " ", s)
    
    # 3) Collapse spaces (Rule A.3)
    s = re.sub(r"\s+", " ", s).strip()
    
    return s

# ==========================================
# 3. Role Normalization
# ==========================================

def normalize_role(role_query: str) -> str:
    """
    Normalize role query to standard format.
    - Handle dots (ผส -> ผส.)
    - Handle spacing (ผจ สบลตน -> ผจ.สบลตน.)
    """
    q = normalize_text(role_query)
    
    # 1. Apply spacing fix for "Prefix Unit" pattern
    # "ผจ สบลตน" -> "ผจ.สบลตน"
    # Logic: If starts with known prefix without dot, add dot.
    prefixes = ["ผส", "ผจ", "ผอ", "ชจญ"]
    for p in prefixes:
        # Pattern: Start with prefix + space + unit
        if re.match(fr"^{p}\s+[a-z0-9ก-๙]+", q):
            q = q.replace(f"{p} ", f"{p}.")
            
        # Pattern: Start with prefix (no dot) + unit (no space)
        # e.g. "ผจสบลตน" -> Hard to detect without knowing unit.
        # But we can try exact prefix match if it's separate word?
        
    # 2. Apply Aliases
    # Simple replacement or token-based?
    # For now, simple replace if matches known tokens
    # Note: ROLE_ALIASES above is minimal.
    
    return q

# ==========================================
# 4. Province Normalization
# ==========================================

def normalize_province(query: str, fuzzy_threshold: float = 0.8) -> Optional[str]:
    """
    Fuzzy match query against known provinces.
    Returns normalized province name or None.
    """
    q_norm = normalize_text(query)
    
    # 1. Check exact/alias first
    if q_norm in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[q_norm]
        
    for p in PROVINCES:
        if p in q_norm:
            return p
            
    # 2. Fuzzy Match (strip "จังหวัด")
    clean_q = q_norm.replace("จังหวัด", "").replace("จ.", "").strip()
    if len(clean_q) < 2: return None
    
    matches = difflib.get_close_matches(clean_q, PROVINCES, n=1, cutoff=fuzzy_threshold)
    if matches:
        return matches[0]
        
    return None

def extract_location_intent(query: str) -> List[str]:
    """
    Extract requested location from query using exact and fuzzy matching.
    Returns list of location names (normalized).
    """
    query_lower = normalize_text(query)
    locations = []
    
    scan_keys = PROVINCES + list(PROVINCE_ALIASES.keys())
    
    # 1. Exact / Scan Logic
    for key in scan_keys:
        if key in query_lower:
            # Normalize to full name if it's an abbr
            full_name = PROVINCE_ALIASES.get(key, key)
            if full_name not in locations:
                locations.append(full_name)
    
    if not locations and len(query_lower) < 20:
         fuzzy = normalize_province(query_lower)
         if fuzzy:
             locations.append(fuzzy)
            
    return list(set(locations))
