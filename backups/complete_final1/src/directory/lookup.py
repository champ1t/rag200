# src/directory/lookup.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    
    # Rule 2: Robust Thai Normalization
    # 2.1 Thai Digits -> Arabic
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    arabic_digits = "0123456789"
    trans_table = str.maketrans(thai_digits, arabic_digits)
    s = s.translate(trans_table)
    
    # 2.2 Fix Common Typos (Shift Key Misses)
    # "ศูนย์๓ูเก็ต" -> "ศูนย์ภูเก็ต"
    s = s.replace("๓ู", "ภู") 
    
    # 2.3 Clean Tone Marks & Zero-width chars
    # Strip zero-width space/joiners
    s = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", s)
    
    # 2.4 Normalize Spacing & Punctuation
    s = s.replace("ภ.", " ").replace("ภ ", " ")
    s = re.sub(r"[\.\(\),/-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


from src.utils.extractors import ABBREVIATIONS

def strip_query(q: str) -> str:
    q = (q or "").strip()
    # Phase 34: Strip organizational prefixes to improve matching
    for k in ["เบอร์โทร", "เบอร์", "โทร", "ติดต่อ", "ขอ", "ของ", "fax", "โทรสาร", "แฟกซ์", "งาน", "ทีม", "กลุ่ม", "ฝ่าย", "สำนักงาน", "สมาชิก"]:
        q = q.replace(k, " ")
    
    # Normalize Abbreviations (New Phase 39)
    q_tokens = q.split()
    expanded = []
    for t in q_tokens:
        expanded.append(ABBREVIATIONS.get(t.lower(), t))
    q = " ".join(expanded)
    
    q = re.sub(r"\s+", " ", q).strip()
    return q


def load_records(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


# -----------------------------
# Step 2) person token match
# -----------------------------
def norm_person_query(q: str) -> str:
    q = norm(strip_query(q))
    q = q.replace("คุณ ", "").replace("คุณ", "").strip()
    q = re.sub(r"\s+", " ", q).strip()
    return q


def person_match_score(q_norm: str, name_norm: str) -> int:
    qtoks = [t for t in q_norm.split() if t]
    if not qtoks:
        return 0
    name_norm = name_norm or ""
    return sum(1 for t in qtoks if t in name_norm)


# -----------------------------
# Step 3) team -> people list
# -----------------------------
def get_people_for_team(team_record: Dict[str, Any], records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    team_name = (team_record.get("name") or "").strip()
    if not team_name:
        return []
    team_norm = norm(team_name)

    people: List[Dict[str, Any]] = []
    for r in records:
        if r.get("type") != "person":
            continue
        tags = r.get("tags") or []
        if any(norm(t) == team_norm for t in tags):
            people.append(r)

    # uniq by name_norm
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for p in people:
        key = p.get("name_norm")
        if key and key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


    return uniq


# ----------------------------------------------
# Phase 228: Strict Matching & Scoring Logic
# ----------------------------------------------

def precompute_record(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule B: Directory Normalization (Pre-compute).
    Adds 'key_norm', 'tokens', 'latin_tokens', 'alias_set' to record.
    """
    if "_precomputed" in r: return r
    
    from src.utils.normalization import normalize_for_matching
    import re
    
    name = r.get("name", "")
    key_norm = normalize_for_matching(name)
    r["key_norm"] = key_norm
    r["tokens"] = set(key_norm.split())
    
    # Extract Latin Tokens (Rule B)
    # e.g. "ศูนย์ omc ภูเก็ต" -> ["omc"]
    r["latin_tokens"] = set(re.findall(r"[a-z0-9]+", key_norm))
    
    # Build Alias Set (Rule B)
    aliases = set()
    aliases.add(key_norm)
    
    # B.1 Remove Noise Words
    noise_words = ["ศูนย์", "ห้อง", "ดูแล", "เทคนิค", "แผนก", "ส่วน", "งาน", "ฝ่าย"]
    clean_name = key_norm
    for w in noise_words:
        clean_name = clean_name.replace(w, " ").strip()
    clean_name = re.sub(r"\s+", " ", clean_name)
    if clean_name and clean_name != key_norm:
        aliases.add(clean_name)
    
    # B.2 Helpdesk Variants
    if "helpdesk" in key_norm:
        aliases.add(key_norm.replace("helpdesk", "help desk"))
    if "help desk" in key_norm:
        aliases.add(key_norm.replace("help desk", "helpdesk"))
        
    # B.3 Optional Hyphens/Dots (Managed by normalization mostly, but implicit concat)
    # e.g. "t-nep" normalized to "t nep". Add "tnep"?
    # logic: if single chars or short words separated by space, concat them
    # naive approach: concat all latin tokens? "ip phone" -> "ipphone"
    latin_concat = "".join(re.findall(r"[a-z0-9]", key_norm))
    if latin_concat and len(latin_concat) > 2:
        aliases.add(latin_concat)
        
    # B.4 Abbreviations (Explicit whitelist)
    # Add common terms to alias set to ensure robust matching?
    # Actually matching logic checks tokens, so just ensuring the name is clean is enough.
    
    r["alias_set"] = aliases
    r["_precomputed"] = True
    return r


# Phase 230: Thai Short-Abbreviation Expansion (Rule H)
ABBR_MAP = {
  "นรา": "นราธิวาส",
  "นครศรี": "นครศรีธรรมราช", 
  "นครศรีฯ": "นครศรีธรรมราช",
  "สุราษ": "สุราษฎร์ธานี",
  "สุราษฯ": "สุราษฎร์ธานี",
  "ยะลา": "ยะลา",
  "ปัตต": "ปัตตานี",
  "สงข": "สงขลา",
  "พังง": "พังงา",
  "ตรัง": "ตรัง",
  "สตูล": "สตูล",
  "พัท": "พัทลุง",
  "ระน": "ระนอง",
  "กระบ": "กระบี่",
  "ชุม": "ชุมพร",
  "ภูเก": "ภูเก็ต",
  "ภูเก็ต": "ภูเก็ต" 
}

EXPANSION_TRIGGERS = ["สื่อสารข้อมูล", "ศูนย์", "ภ.", "help desk", "ส่วน", "งาน", "ทีม", "edimax", "zte", "huawei"]
BROAD_CATEGORIES = {"noc", "สื่อสารข้อมูล", "สผ", "helpdesk", "help desk", "ip phone", "ip-phone", "edimax", "csoc", "cpe", "access", "core", "metro", "wifi"}

# Phase 236: Vendor/Special Product Mapping (Rule BR-2)
VENDOR_CONTACTS = {
    "edimax": "ติดต่อฝ่ายเทคนิค King Intelligent Technology (ผู้แทนจำหน่าย Edimax) หรือเบอร์ Helpdesk WiFi (3408)",
    "zte": "ติดต่อทีม Core Network / Access Network (ฝ่ายอุปกรณ์ Huawei/ZTE)",
    "huawei": "ติดต่อทีม Core Network / Access Network (ฝ่ายอุปกรณ์ Huawei/ZTE)"
}

# Province/city names that by themselves indicate a broad location query
# (no department or person qualifier -> must show all matching contacts)
LOCATION_ONLY_TERMS = {
    # Southern Thailand provinces
    "นราธิวาส", "นครศรีธรรมราช", "สุราษฎร์ธานี", "ยะลา", "ปัตตานี",
    "สงขลา", "พังงา", "ตรัง", "สตูล", "พัทลุง", "ระนอง", "กระบี่",
    "ชุมพร", "ภูเก็ต",
    # Common city/district names used by staff
    "หาดใหญ่", "hat yai", "ภาคใต้", "south", "ใต้",
    "กรุงเทพ", "bkk", "bangkok",
    "เชียงใหม่", "chiangmai",
    "ขอนแก่น", "khonkaen",
    "นครราชสีมา", "โคราช",
    "อุดร", "อุดรธานี",
}


def is_broad_query(q_norm: str) -> bool:
    """Rule I: Check if query is just a broad category (no specific unit/person).

    Returns True if query is:
    - A known broad category (NOC, helpdesk, etc.)
    - A pure location/province name with no additional qualifier
    """
    q_stripped = q_norm.strip().lower()
    # Original checks
    if q_stripped in BROAD_CATEGORIES or q_stripped in EXPANSION_TRIGGERS:
        return True
    # New: pure location-only query -> show all contacts for that area
    if q_stripped in LOCATION_ONLY_TERMS:
        return True
    return False

def expand_query(q_norm: str) -> Tuple[str, bool]:
    """
    Rule H: Expand short abbreviations if preceded by category trigger.
    Returns (expanded_query, is_expanded)
    """
    # 1. Check for triggers
    trigger_found = None
    suffix = ""
    
    # Sort triggers by length desc to match longest first
    for t in sorted(EXPANSION_TRIGGERS, key=len, reverse=True):
        idx = q_norm.find(t)
        if idx != -1:
            # Check suffix
            potential_suffix = q_norm[idx + len(t):].strip()
            if potential_suffix:
                trigger_found = t
                suffix = potential_suffix
                break
    
    if not trigger_found or not suffix:
        return q_norm, False

    # 2. Check Abbreviation Map
    expanded_suffix = ABBR_MAP.get(suffix)
    
    # Prefix match if not direct match
    if not expanded_suffix:
        # Check if suffix is a prefix of any key in ABBR_MAP (length >= 2)
        if len(suffix) >= 2:
            candidates = []
            for k, v in ABBR_MAP.items():
                if k.startswith(suffix) or v.startswith(suffix): 
                     candidates.append(v)
            if candidates:
                expanded_suffix = candidates[0]

    if expanded_suffix:
        # Use the original trigger text found + Expanded Suffix
        return f"{trigger_found} {expanded_suffix}", True
        
    return q_norm, False

def lookup_phones(q: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rule C: Matching & Scoring (4-Tier).
    """
    from src.utils.normalization import normalize_for_matching
    # Internal Levenshtein helper (avoid dependency)
    def lev_dist(s1, s2):
        if len(s1) < len(s2):
            return lev_dist(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
    
    # 1. Normalize Query
    q_norm = normalize_for_matching(q)
    
    # 1. Normalize Query
    q_norm = normalize_for_matching(q)
    
    # Rule H: Abbreviation Expansion
    q_expanded, is_expanded = expand_query(q_norm)
    # Use expanded query for matching if available
    q_match = q_expanded if is_expanded else q_norm
    
    q_tokens = set(q_match.split())
    q_latin = {t for t in q_tokens if re.match(r"^[a-zA-Z0-9]+$", t)}
    
    candidates = []

    for r in records:
        score = 0
        match_type = "none"
        
        # Ensure precomputed
        if not r.get("_precomputed"):
            precompute_record(r)
            
        key_norm = r["key_norm"]
        
        # 4-Tier Scoring (Phase 228)
        
        # Tier 1: Exact Match (100)
        if q_match == key_norm or q_match in r["alias_set"]:
            score = 100
            match_type = "exact"
        # Tier 2: Strong Token Match (90)
        # All query tokens must be in record tokens
        elif not score and q_tokens.issubset(r["tokens"]):
            score = 90
            match_type = "token_strong"
            
        # Tier 3: Partial Token Overlap (75)
        # At least 50% of query tokens match AND (if query has latin) at least 1 latin match
        elif not score:
            intersection = q_tokens.intersection(r["tokens"])
            if intersection:
                ratio = len(intersection) / len(q_tokens)
                latin_match = not q_latin or not q_latin.isdisjoint(r["latin_tokens"])
                
                if ratio >= 0.5 and latin_match:
                     score = 75
                     match_type = "token_partial"
        
        # Tier 4: Fuzzy Match (60)
        # Only if no strong/partial match
        elif not score:
            # Check Levenshtein against name and aliases
            # Allow dist 2 for short, 3 for long
            threshold = 2 if len(search_q) <= 10 else 3
            
            d_name = lev_dist(search_q, key_norm)
            if d_name <= threshold:
                score = 60
                match_type = "fuzzy"
            else:
                # Check aliases
                for alias in r["alias_set"]:
                    if lev_dist(search_q, alias) <= threshold:
                        score = 60
                        match_type = "fuzzy_alias"
                        break
        
        if score >= 60:
            # Clone and add score
            c = r.copy()
            c["_score"] = score
            c["_match_type"] = match_type
            candidates.append(c)
            
    # Sort by score desc, then name
    candidates.sort(key=lambda x: (-x["_score"], x["name"]))
    
    # People Logic for Team matches (Rule C)
    for c in candidates:
        if c.get("type") == "team" and not c.get("people"):
             c["people"] = get_people_for_team(c, records)
             
    return candidates
    
    # Rare Token Priority (Rule C.2 Special)
    rare_tokens = {"iig", "t-nep", "tnep", "cnema", "mdes", "ntmobile", "nt2", "csoc", "rnoc", "noc"}
    has_rare = any(t in rare_tokens for t in q_tokens)
    
    candidates = []
    
    for r in records:
        # Ensure precomputed
        if "_precomputed" not in r:
            precompute_record(r)
            
        r_key = r["key_norm"]
        r_aliases = r["alias_set"]
        r_tokens = r["tokens"]
        
        score = 0
        match_type = "none"
        
        # -----------------------------
        # Tier 1: Exact Match (100)
        # -----------------------------
        if q_norm == r_key or q_norm in r_aliases:
            score = 100
            match_type = "exact"
            
        # -----------------------------
        # Tier 2: Strong Token Match (90)
        # -----------------------------
        elif score == 0 and q_tokens.issubset(r_tokens):
            score = 90
            match_type = "token_strong"
            # Boost if rare token match
            if has_rare and not q_latin.isdisjoint(r["latin_tokens"]):
                 score += 5 # 95
        
        # -----------------------------
        # Tier 3: Partial Token Overlap (75)
        # -----------------------------
        elif score == 0:
            # Significant overlap?
            # intersection / len(q_tokens) >= 0.6?
            if not q_tokens.isdisjoint(r_tokens):
                 common = q_tokens.intersection(r_tokens)
                 coverage = len(common) / len(q_tokens)
                 
                 # Logic: If query has latin tokens, match MUST share at least one.
                 # e.g. "csoc" query shouldn't match "omc" even if text overlaps (unlikely but safe)
                 latin_match = True
                 if q_latin:
                     latin_match = not q_latin.isdisjoint(r["latin_tokens"])
                 
                 if coverage >= 0.5 and latin_match:
                     score = 75
                     match_type = "partial"
                     
                     # Boost for rare
                     if has_rare and not q_latin.isdisjoint(r["latin_tokens"]):
                         score += 5 # 80

        # -----------------------------
        # Tier 4: Fuzzy Match (60)
        # -----------------------------
        # Rule: len<=10 dist<=2, len>10 dist<=3
        if score == 0:
            allowed_dist = 2 if len(q_norm) <= 10 else 3
            # Check against key and aliases
            # Optimization: check length diff first
            d = lev_dist(q_norm, r_key)
            if d <= allowed_dist:
                score = 60
                match_type = "fuzzy"
            else:
                # Check aliases
                for a in r_aliases:
                    if abs(len(a) - len(q_norm)) > allowed_dist: continue
                    if lev_dist(q_norm, a) <= allowed_dist:
                        score = 60
                        match_type = "fuzzy"
                        break
        
        # Special Latin Transposition/Typo Rule (Rule C.3)
        # "ipphone" vs "ip phone" handled by alias/normalization
        
        if score >= 60:
            # Inject Score
            hit = dict(r)
            hit["_score"] = score
            hit["_match_type"] = match_type
            
            # Expand people if Team
            if hit.get("type") == "team":
                 hit["people"] = get_people_for_team(hit, records)
                 
            candidates.append(hit)
            
    # Sort
    candidates.sort(key=lambda x: (x["_score"], x.get("name", "")), reverse=True)
    return candidates


def generate_suggestions(query: str, records: List[Dict[str, Any]], top_k=3) -> List[str]:
    """
    Rule G: Suggest close matches for failed query.
    """
    from src.utils.normalization import normalize_for_matching
    
    # Internal Levenshtein helper
    def lev_dist(s1, s2):
        if len(s1) < len(s2):
            return lev_dist(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
    
    q_norm = normalize_for_matching(query)
    suggestions = []
    
    # Collect all keys/aliases
    all_keys = []
    for r in records:
        if "_precomputed" not in r: precompute_record(r)
        all_keys.append(r["key_norm"])
        
    # Sort by edit distance
    all_keys.sort(key=lambda k: lev_dist(q_norm, k))
    
    # Pick top K unique
    seen = set()
    for k in all_keys:
        if k not in seen and k != q_norm:
            suggestions.append(k)
            seen.add(k)
        if len(suggestions) >= top_k: break
        
    return suggestions


# -----------------------------
# Reverse Lookup (by phone)
# -----------------------------
def lookup_by_phone(q: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Normalize query: strip all non-digits
    q_digits = re.sub(r"\D", "", q)
    if not q_digits:
        return []

    hits = []
    for r in records:
        phones = r.get("phones") or []
        # Check if any phone in the record contains the query digits (or matches strictly?)
        # For now, let's try strict substring match of digits
        # e.g. q="025757222" -> r_phone="02-575-7222" -> r_digits="025757222" -> MATCH
        
        match = False
        for p in phones:
            p_digits = re.sub(r"\D", "", p)
            if q_digits in p_digits:
                match = True
                break
        
        if match:
            hits.append(r)
            
    return hits

ROLE_ALIASES = {
    "ผจ": "ผจ.สบลตน.", "ผส": "ผส.บลตน.", "manager": "ผจ.สบลตน.",
    "director": "ผส.", "admin": "ผู้ดูแลระบบ", "administrator": "ผู้ดูแลระบบ"
}

