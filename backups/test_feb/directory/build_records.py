from __future__ import annotations

print("[DEBUG] build_records.py LOADED")

import json
import re
from pathlib import Path
from typing import List


# รองรับ: 0-xxxx-xxxx (9 digits), 0xx-xxxx..., 0xxxxxxxxx
# รองรับ Range suffix: -1, -12
PHONE_RE = re.compile(
    r"((?:0\d{1,2}[- ]?\d{3,4}[- ]?\d{3,4}(?:-\d{1,4}){0,2}|0[- ]?\d{4}[- ]?\d{4}(?:-\d{1,4}){0,2}|0[- ]?\d{5}[- ]?\d{3}(?:-\d{1,4}){0,2}|0\d{8,9}(?:-\d{1,4}){0,2}|\d{4}-\d{4}(?:-\d{1,4}){0,2})"
    r"(?:.*?(?:กด|ต่อ|ext\.?|#)\s*(\d+))?)",
    re.IGNORECASE
)

# (ADD) person parser (optional; not required by split-version below)
PERSON_SPLIT_RE = re.compile(r"(คุณ\s*[^\d|]+?)(?=(คุณ\s*|$))")


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("ภ.", " ").replace("ภ ", " ")
    s = re.sub(r"[\.\(\),/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# =========================================================
# 2.1 validate_phone_digits (ตัวคัดกรองเดียว) ✅ REPLACED
# =========================================================
def validate_phone_digits(digits: str) -> bool:
    if not digits:
        return False

    # Mobile: 10 digits, starts with 06, 08, 09
    if len(digits) == 10 and digits[:2] in {"06", "08", "09"}:
        return True

    # Landline BKK: 9 digits, starts with 02
    if len(digits) == 9 and digits.startswith("02"):
        return True
    
    # Landline Provincial: 9 digits, starts with 03, 04, 05, 07
    if len(digits) == 9 and digits[:2] in {"03", "04", "05", "07"}:
        return True

    # Legacy org number (8 digits) – assume Bangkok
    if len(digits) == 8:
        return True

    return False


# =========================================================
# 2.2 normalize_phone (ไม่เดาอีกต่อไป) ✅ REPLACED
# =========================================================
def normalize_phone(raw: str) -> tuple[str | None, str | None]:
    if not raw:
        return None, None

    s = raw.strip()

    # ---- extract extension ----
    ext = None
    m_ext = re.search(r"(?:#|ต่อ|กด|ext\.?)\s*(\d{1,4})", s, re.I)
    if m_ext:
        ext = m_ext.group(1)
        s = s[: m_ext.start()]

    digits = re.sub(r"\D", "", s)

    if not validate_phone_digits(digits):
        return None, None

    # ---- Mobile ----
    if len(digits) == 10 and digits[:2] in {"06", "08", "09"}:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", ext

    # ---- Bangkok landline ----
    if digits.startswith("02"):
        return f"02-{digits[2:5]}-{digits[5:]}", ext

    # ---- Provincial landline ----
    if digits.startswith("0") and digits[1] != "2":
        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", ext
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", ext

    # ---- Legacy 8-digit (Bangkok only) ----
    if len(digits) == 8:
        return f"02-{digits[:3]}-{digits[3:]}", ext

    return None, None



def expand_phone_ranges(raw_token: str) -> List[str]:
    """
    Handle ranges like:
      0-2575-4750-5 -> [0-2575-4750, 0-2575-4755] (Discrete)
      0-2575-4602-3 -> [0-2575-4602, 0-2575-4603]
      02-575-9531-2 -> [02-575-9531, 02-575-9532]
    Assumption: The last part is a single digit suffix meant to replace the very last digit of the base number.
    """
    # Pattern: ends with "-d" (hyphen digit)
    # Check if we have that pattern
    match = re.search(r"^(.*?)-(\d)$", raw_token)
    if not match:
        return [raw_token]
    
    base = match.group(1)
    suffix = match.group(2)
    
    # We need to verify 'base' acts like a phone number
    # Normalize base matching regex logic or just heuristics
    # If base looks like a phone number (digits >= 8), we try to replace/append
    
    # Case: Replace last digit
    # 0-2575-4750 -> 0-2575-475 + 5 -> 0-2575-4755
    # Logic: Remove last char from base (if digit) and append suffix?
    # Or strict replacement?
    
    # Let's count digits in base
    base_digits = re.sub(r"\D", "", base)
    
    # 02 numbers: base should be 9 digits (fully formed)
    # Mobile: 10 digits
    
    # If base is valid phone, and we have a suffix.
    # We output [base, modified_base]
    
    if not validate_phone_digits(base_digits):
        # Maybe base is valid but structured weirdly?
        # If not valid, maybe we shouldn't expand?
        # But wait, 0-2575-4750 is valid (9 digits).
        return [raw_token]

    # Construct variant:
    # Remove last DIGIT from base, append suffix
    # We need to find the last identifier digit in 'base'
    # E.g. "0-2575-4750" -> index of '0' at end
    
    # Find last digit index
    last_digit_idx = -1
    for i in range(len(base) - 1, -1, -1):
        if base[i].isdigit():
            last_digit_idx = i
            break
            
    if last_digit_idx == -1:
        return [raw_token]
        
    # Construct new string
    # "0-2575-475" + suffix + "" (if any trailing chars, none here due to regex)
    variant = base[:last_digit_idx] + suffix + base[last_digit_idx+1:]
    
    return [base, variant]


# =========================================================
# 2.3 parse_phones (ไม่ต้องแตะ logic อื่น) ✅ (same logic)
# =========================================================
def parse_phones(text: str) -> List[str]:
    out: List[str] = []

    for m in PHONE_RE.findall(text or ""):
        token = m[0] if isinstance(m, tuple) else m

        # (NEW) Expand ranges
        expanded_tokens = expand_phone_ranges(token)
        
        for t in expanded_tokens:
            number, ext = normalize_phone(t)
            if not number:
                continue

            if ext:
                out.append(f"{number} กด {ext}")
            else:
                out.append(number)

    # uniq keep order
    seen = set()
    uniq: List[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def build_directory_records(processed_dir: str, directory_url_substr: str, out_path: str) -> int:
    # ✅ debug: เช็คว่าถูกไฟล์/ถูกฟังก์ชันจริง
    print("[DEBUG] build_directory_records() CALLED")

    pdir = Path(processed_dir)
    if not pdir.exists():
        raise FileNotFoundError(f"processed_dir not found: {processed_dir}")

    # หา URL ของหน้า directory (id=64)
    target = None
    for p in pdir.glob("*.json"):
        j = json.loads(p.read_text(encoding="utf-8"))
        if directory_url_substr in (j.get("url", "")):
            target = j
            break
    if not target:
        raise RuntimeError(f"Directory page not found for substring: {directory_url_substr}")

    text = target.get("text", "") or ""
    url = target.get("url", "")

    records = []
    current_team = None  # State machine context

    for ln in text.splitlines():
        ln_stripped = ln.strip()
        if not ln_stripped:
            continue

        # Check if line is a header/context (Heuristic: no pipe, short length, not noise)
        if "|" not in ln_stripped:
            # Simple heuristic: treat lines with minimal keywords or length as headers
            # Ignore common noise lines
            noise = {"Today", "Yesterday"}
            if any(n in ln_stripped for n in noise):
                continue
            
            # Additional heuristic: If it looks like a section header (e.g. ADSL, NMS, etc.)
            # For now, just accept non-empty lines that are likely headers.
            # Maybe limit length to avoid capturing long paragraph text?
            if len(ln_stripped) < 100:
                current_team = ln_stripped
            continue

        # Clean parts: remove empty strings from pipe split
        # This handles "| seq | name | phone | seq | ..." sequences
        parts = [x.strip() for x in ln.split("|") if x.strip()]
        
        # Skip lines that don't have enough data for at least one record (Seq, Name, Phone)
        # Note: sometimes only Name|Phone exists? (2 parts). 
        # But our previous observed structure was Seq|Name|Phone (3 parts).
        # Let's keep strict check to avoid noise, or relax if needed.
        if len(parts) < 3:
            continue

        # Iterate in chunks of 3
        i = 0
        while i + 2 < len(parts):
            name = parts[i+1]
            phone_blob = parts[i+2]
            
            # (Guardrail) Parsing Safeguard:
            # If the phone column is suspiciously long (e.g. merged rows), skip it.
            # This prevents creating a single record that "owns" all subsequent numbers.
            if len(phone_blob) > 200:
                # Log this as a warning if needed, or just skip
                # print(f"[WARN] Skipping giant phone blob for name='{name}': {len(phone_blob)} chars")
                i += 3
                continue
            
            phones = parse_phones(phone_blob)
            
            if phones and name:
                 # Calculate tags: use current_team context + own name
                row_tags = [name.strip()]
                if current_team:
                    row_tags.insert(0, current_team)

                 # (ADD) แตก record บุคคล ถ้ามี "คุณ ..."
                if "คุณ" in phone_blob:
                    pparts = re.split(r"(?=คุณ\s)", phone_blob)
                    for part in pparts:
                        part = part.strip()
                        if not part.startswith("คุณ"):
                            continue

                        m = re.search(r"(0\d|\d{4}-\d{4})", part)
                        name_part = part if not m else part[: m.start()]
                        person_name = re.sub(r"\s+", " ", name_part).strip()

                        person_phones = parse_phones(part)
                        if person_name and person_phones:
                            records.append({
                                "name": person_name,
                                "name_norm": norm(person_name),
                                "phones": person_phones,
                                "source_url": url,
                                "row_text": ln.strip(),
                                "tags": row_tags,
                                "type": "person",
                            })

                # (CHANGE) record หลักเดิม (ทีม/งาน)
                records.append({
                    "name": name.strip(),
                    "name_norm": norm(name),
                    "phones": phones,
                    "source_url": url,
                    "row_text": ln.strip(),
                    "tags": row_tags,
                    "type": "team",
                })
            
            i += 3

    # Deduplicate Records
    # Key: (name_norm, sorted_phones_tuple, source_url)
    unique_records = []
    seen = set()
    
    for r in records:
        # Create a unique key
        # We sort phones to ensure order doesn't matter for dedup
        p_tuple = tuple(sorted(r["phones"]))
        key = (r["name_norm"], p_tuple, r["source_url"])
        
        if key not in seen:
            seen.add(key)
            unique_records.append(r)
            
    # Write to jsonl
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in unique_records) + "\n",
        encoding="utf-8"
    )

    # ===== DEBUG SUMMARY (TEMP) =====
    team_n = sum(1 for r in unique_records if r.get("type") == "team")
    person_n = sum(1 for r in unique_records if r.get("type") == "person")
    print(f"[DEBUG] records_total={len(unique_records)} (deduped from {len(records)}) team={team_n} person={person_n}")
    for r in [x for x in unique_records if x.get("type") == "person"][:3]:
        print("[DEBUG] person_sample:", r.get("name"), r.get("phones"), "tags=", r.get("tags"))
    # ===== END DEBUG =====

    return len(unique_records)
