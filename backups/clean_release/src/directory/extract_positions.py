import json
import re
from pathlib import Path
import html

def extract_emails_from_html(content):
    lines = content.splitlines()
    var_map = {} 
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        m_init = re.search(r"var\s+(addy\d+)\s*=\s*(.*);", line)
        if m_init:
            var_name = m_init.group(1)
            var_map[var_name] = m_init.group(2)
            continue
            
        m_add = re.search(r"(addy\d+)\s*=\s*\1\s*\+\s*(.*);", line)
        if m_add:
            var_name = m_add.group(1)
            added_expr = m_add.group(2)
            if var_name in var_map:
                var_map[var_name] += " + " + added_expr
                
    final_emails = []
    for var, full_expr in var_map.items():
        parts = re.findall(r"['\"](.*?)['\"]", full_expr)
        combined = "".join(parts)
        decoded = html.unescape(combined)
        if "@" in decoded and "." in decoded:
            final_emails.append(decoded)
            
    return list(set(final_emails))

    return list(set(final_emails))

def is_valid_person_line(line):
    """
    STRICT FILTER: Returns True if line contains strong person signals.
    - Thai Honorifics
    - English Honorifics
    - Email Pattern
    - Phone Pattern
    """
    # 1. Honorifics
    honorifics = [
        "นาย", "นาง", "น.ส", "น.s", "ว่าที่", "คุณ", "ดร.", "ผศ.", "รศ.", "ศ.", 
        "Mr.", "Mrs.", "Ms.", "Dr."
    ]
    if any(h in line for h in honorifics): return True
    
    # 2. Email
    if re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", line): return True
    
    # 3. Phone (Strict Pattern)
    # Case A: Standard Thai Mobile/Landline (0xx-xxx-xxxx) -> 0 followed by digits
    if re.search(r"\b0\d{1,2}[- ]?\d{3,4}[- ]?\d{3,4}", line): return True
    # Case B: Service Number (0-xxxx-xxxx)
    if re.search(r"\b0[- ]\d{3,4}[- ]?\d{3,4}", line): return True
    
    return False

def collect_raw_positions():
    processed_dir = Path("data/processed")
    out_file = Path("data/records/positions.jsonl")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    positions = []
    
    # 1. Target specific known personnel files
    # Itemid_59: บุคลากร SMC
    # Itemid_60: ผส.บลตน. (Director)
    # Itemid_56: ผจ.สบลตน. (Manager)
    
    files = list(processed_dir.glob("*.json"))
    
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            url = data.get("url", "")
            title = data.get("title", "")
            text = data.get("text", "")
            raw_path = data.get("raw_file", "")
            
            # --- Strategy 1: Explicit Director/Manager Pages ---
            # Use Title matching as it is cleaner than URL params
            
            is_director = False
            is_manager = False
            
            if title.strip() == "ผส.บลตน.":
                is_director = True
            elif title.strip() == "ผจ.สบลตน.":
                is_manager = True
            elif "id=56" in url and "Itemid=60" in url: # Fallback strict
                 is_manager = True
            
            # --- Strategy 3: Admin Page (Itemid=59) ---
            is_admin = False
            if title.strip() == "ผู้ดูแลระบบ" or ("id=57" in url and "Itemid=59" in url):
                is_admin = True
                            
            if is_director or is_manager or is_admin:
                # Common extraction for Strategy 1 & 3
                if is_director: role = "ผส.บลตน."
                elif is_manager: role = "ผจ.สบลตน."
                else: role = "ผู้ดูแลระบบ"
                
                # Extract Name
                # Admin page format: <p>คุณ ชัยยา จิตรพรหม</p>
                # The generic regex might catch it: (คุณ)([^\s]+)\s+([^\s]+)
                # But sometimes "ตำแหน่ง" is not present on Admin page.
                
                name = ""
                # Try strict full pattern first (with Position)
                m_name = re.search(r"(นาย|นาง|น\.ส\.|คุณ)([^\s]+)\s+([^\s]+)\s+ตำแหน่ง\s+([^\n]+)", text)
                if m_name:
                    name = f"{m_name.group(1)}{m_name.group(2)} {m_name.group(3)}"
                elif is_admin:
                    # Admin page might just have name line
                    # Look for "คุณ ..."
                    m_name_simple = re.search(r"(นาย|นาง|น\.ส\.|คุณ)\s*([^\s]+)\s+([^\s]+)", text)
                    if m_name_simple:
                         name = f"{m_name_simple.group(1)}{m_name_simple.group(2)} {m_name_simple.group(3)}"
                
                # Extract Phones
                # Pattern: "โทร : 074..." or "โทร. 074..."
                phones = []
                m_phone = re.search(r"โทร\s*[:.]\s*([0-9\-, #]+)", text)
                if m_phone:
                     raw_phones = m_phone.group(1).split(',')
                     for p in raw_phones:
                         p = p.strip()
                         if p: phones.append(p)
                
                # Extract Fax
                # Pattern: "โทรสาร : ...", "Fax : ...", "F : ...", "แฟกซ์ : ..."
                fax_nums = []
                m_fax = re.search(r"(?:โทรสาร|Fax|แฟกซ์|F)\s*[:.]\s*([0-9\-, #]+)", text, re.IGNORECASE)
                if m_fax:
                     raw_fax = m_fax.group(1).split(',')
                     for f in raw_fax:
                         f = f.strip()
                         if f: fax_nums.append(f)
                
                # Extract Email from Raw HTML (Joomla Cloaking)
                emails = []
                if raw_path:
                    raw_file = Path(raw_path)
                    if raw_file.exists():
                        raw_content = raw_file.read_text(encoding="utf-8", errors="ignore")
                        emails = extract_emails_from_html(raw_content)

                if name:
                    positions.append({
                        "role": role, 
                        "name": name, 
                        "source": url,
                        "phones": phones,
                        "faxes": fax_nums,
                        "emails": emails
                    })
            
            # --- Strategy 2: Personnel List (Itemid_64) ---
            # Title might be "ผู้รับผิดชอบงานต่างๆ" or "บุคลากร SMC" depending on version
            elif "Itemid=64" in url or "ผู้รับผิดชอบงานต่างๆ" in title:
                # Parsing logic for:
                # "งาน FTTx ... tel:..."
                # [List of names]
                # "งาน HelpDesk ..."
                
                lines = text.split('\n')
                current_group = None
                current_phones = []
                
                # Heuristic:
                # 1. "งาน ..." starts a group
                # 2. "Supervisor Agent" starts a group
                # 3. "Agent" starts a group (unless part of Supervisor)
                
                
                # Regex for Thai Name:
                # Prefix (Optional) + First Name + Last Name + Nickname (Optional)
                # We need to be careful not to match random text.
                # Valid Thai characters: \u0E00-\u0E7F
                
                # Known prefixes to help identify likely names, but we allow missing prefix too.
                prefixes = r"(?:นาย|นาง|น\.s\.|น\.ส\.|ว่าที่(?:ร\.ต\.|ร\.ท\.)?|คุณ|ดร\.)"
                
                # Stop words/patterns that indicate END of a group if encountered in a line that doesn't also look like a header
                stop_patterns = ["*83", "*84", "โทร", "Pause", "Unpause", "Joomla", "Visitors"]
                
                # Clean up existing positions to ensure we don't have dupes from previous logic
                # Actually checking uniqueness at the end of function is fine, but we want to capture correctly here.
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # 1. Detect Boundaries / New Headers
                    is_new_header = False
                    
                    # Pattern: "Agent 0-..." or "งาน ..." or "Supervisor ..."
                    # Check "Supervisor Agent" FIRST because "Agent" is a substring of it.
                    if line.startswith("Supervisor Agent") or "Supervisor" in line:
                         current_group = "Supervisor Agent"
                         is_new_header = True
                    elif line.startswith("Agent") or ("Agent" in line and "0-7427-3444" in line):
                         current_group = "Agent"
                         is_new_header = True
                    elif line.startswith("งาน ") or "งาน FTTx" in line or "งาน HelpDesk" in line or "Management" in line:
                         if "FTTx" in line: current_group = "งาน FTTx"
                         elif "HelpDesk" in line: current_group = "งาน HelpDesk"
                         elif "Management" in line: current_group = "งาน Management SMC"
                         else:
                             m_grp = re.match(r"(งาน\s*[^\s(]+)", line)
                             current_group = m_grp.group(1) if m_grp else "งาน General"
                         is_new_header = True
                         
                    if is_new_header:
                        # Extract phones from this header line
                        # Look for "tel:..." or independent numbers like "0-7427-3444"
                        current_phones = []
                        # Regex for phones: 0-xxxx-xxxx or 0xxxxxxxxx, maybe with ext
                        # Capture strict patterns to avoid extracting other numbers
                        found_phones = re.findall(r"0-?\d{3,4}-?\d{3,4}(?:\s*(?:#|ext\.?)\s*\d+)?", line)
                        for p in found_phones:
                            current_phones.append(p.strip())
                          
                    # Check for Stop Signals (if not a header)
                    if not is_new_header and current_group:
                        if any(s in line for s in stop_patterns):
                             # Only stop if it's strictly a stop line, 
                             # but "ปฐมพงศ์ ... *83" might be on same line? 
                             # The file content shows "*83" as separate tokens or lines.
                             # If line *starts* with *, it's likely a command.
                             if line.startswith("*"):
                                 current_group = None
                                 current_phones = []
                                 continue
                    
                    # 2. Extract Names (if in a group)
                    if current_group:
                        # Strategy: Find all candidate patterns
                        # Pattern: (Prefix)? \s* (ThaiWord) \s+ (ThaiWord) (\s*\(.*?\))?
                        # We must enforce valid Thai chars for Name/Surname to avoid matching "0-7425-0685 #300" as a name.
                        
                        # \u0E00-\u0E7F is Thai range.
                        
                        # Improved Regex:
                        # (Prefix)? \s* ([ก-๙A-Za-z]+) \s+ ([ก-๙A-Za-z]+) (?:\s*(\(.*?\)))?
                        # Added A-Za-z just in case, but mostly Thai.
                        
                        # Using verbose regex for clarity
                        pattern = re.compile(r"""
                            (?:(นาย|นาง|น\.s\.|น\.ส\.|ว่าที่(?:ร\.ต\.|ร\.ท\.)?|คุณ|ดร\.)\s*)?  # Optional Prefix Group 1
                            ([ก-๙]{2,})                  # First Name (at least 2 thai chars) Group 2
                            \s+                          # Space
                            ([ก-๙]{2,})                  # Last Name (at least 2 thai chars) Group 3
                            (?:\s*\((\S+?)\))?           # Optional Nickname in parens Group 4
                        """, re.VERBOSE)
                        
                        matches = pattern.finditer(line)
                        for m in matches:
                            prefix = m.group(1) or ""
                            first = m.group(2)
                            last = m.group(3)
                            nickname = m.group(4) or ""
                            
                            # Filter out false positives
                            # e.g. "งาน FTTx" might match "งาน" as prefix? No, "งาน" is not in prefix list.
                            # "สมบูรณ์ เชาวน์..." is valid.
                            
                            # Skip if "โทร" or "Fax" appears in name slots (unlikely with [ก-๙] regex but possible)
                            if "โทร" in first or "โทร" in last: continue
                            
                            full_name = f"{prefix}{first} {last}"
                            if nickname:
                                full_name += f" ({nickname})"
                            
                            full_name = full_name.strip()
                            
                            # STRICT CHECK (Phase 70)
                            # Must be a valid person line context or have person keywords
                            # We already used a strict Regex for Name ([ก-๙]{2,}) so it's likely a person.
                            # But let's double check against garbage like "ลิงค์ ... ภก"
                            
                            # Heuristic: If name contains "ลิงค์" or "ศูนย์" or "ระบบ" -> Reject
                            stop_words = ["ลิงค์", "ศูนย์", "ระบบ", "service", "menu", "main", "หน้าหลัก", "ปรับปรุง", "visitor"]
                            if any(w in full_name.lower() for w in stop_words):
                                continue
                                
                            positions.append({
                                "role": current_group,
                                "name": full_name,
                                "source": url,
                                "phones": current_phones, # Attach group phones
                                "faxes": [],
                                "emails": []
                            })
                            
        except Exception as e:
            print(f"Error processing {p.name}: {e}")
            continue
            
    return positions

def merge_entities(positions):
    """
    Merge raw position records by (Role, Name).
    Tracks provenance of phones/emails.
    """
    merged = {}
    
    for p in positions:
        # Normalize Key: (Role, CleanName)
        r_key = p["role"].strip()
        n_key = re.sub(r"\s+", "", p["name"]).lower() 
        
        key = (r_key, n_key)
        
        if key not in merged:
            # Init new record
            # Normalize phones for initial map
            init_phones_map = {}
            for ph in p["phones"]:
                norm = ph.replace("-", "").replace(" ", "").strip()
                if not norm: continue
                if norm not in init_phones_map: init_phones_map[norm] = set()
                init_phones_map[norm].add(p["source"])
            
            merged[key] = {
                "role": p["role"],
                "name": p["name"],
                "phones_map": init_phones_map, 
                "emails_map": {em: {p["source"]} for em in p["emails"]}, 
                "faxes": set(p["faxes"]), 
                "sources": {p["source"]}
            }
        else:
            # Merge into existing
            if len(p["name"]) > len(merged[key]["name"]):
                merged[key]["name"] = p["name"]
            
            # Merge Phones Source Map
            for ph in p["phones"]:
                norm = ph.replace("-", "").replace(" ", "").strip()
                if not norm: continue
                if norm not in merged[key]["phones_map"]:
                    merged[key]["phones_map"][norm] = set()
                merged[key]["phones_map"][norm].add(p["source"])
            
            # Merge Emails Source Map
            for em in p["emails"]:
                if em not in merged[key]["emails_map"]:
                    merged[key]["emails_map"][em] = set()
                merged[key]["emails_map"][em].add(p["source"])
                
            merged[key]["faxes"].update(p["faxes"])
            merged[key]["sources"].add(p["source"])
            
    # Convert sets back to sorted lists
    final_records = []
    for k, v in merged.items():
        # Convert maps to JSON-serializable structure
        phone_sources = {ph: sorted(list(srcs)) for ph, srcs in v["phones_map"].items()}
        email_sources = {em: sorted(list(srcs)) for em, srcs in v["emails_map"].items()}
        
        rec = {
            "role": v["role"],
            "name": v["name"],
            "phones": sorted(list(v["phones_map"].keys())), 
            "emails": sorted(list(v["emails_map"].keys())), 
            "faxes": sorted(list(v["faxes"])),
            "sources": sorted(list(v["sources"])),
            "phone_sources": phone_sources, 
            "email_sources": email_sources 
        }
        final_records.append(rec)
    return final_records

def summarize_teams(records):
    """
    Group records by Role (Team) -> Team Record.
    Output:
    {
      "team": "งาน FTTx",
      "members": [
         {"name": "...", "phones": [...], "role": "..."} 
      ],
      "source": "..." (First source found)
    }
    """
    teams = {}
    for r in records:
        role = r["role"]
        # Normalize Role? 
        # For now, use exact role from extraction as key.
        if role not in teams:
            teams[role] = {
                "team": role,
                "members": [],
                "sources": set()
            }
        
        teams[role]["members"].append({
            "name": r["name"],
            "phones": r["phones"],
            "emails": r["emails"]
        })
        teams[role]["sources"].update(r["sources"])
        
    final_teams = []
    for k, v in teams.items():
        # STRICT FILTER (Phase 70)
        # Discard team if 0 members
        if not v["members"]:
            continue
            
        rec = {
            "team": v["team"],
            "members": v["members"], # Already sorted by insertion order (Scraping order)
            "sources": sorted(list(v["sources"]))
        }
        final_teams.append(rec)
    return final_teams

def extract_positions():
    positions = collect_raw_positions()
    final_records = merge_entities(positions)
    
    out_file = Path("data/records/positions.jsonl")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_file, "w", encoding="utf-8") as f:
        for p in final_records:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            
    # Also export Teams
    teams = summarize_teams(final_records)
    out_team = Path("data/records/teams.jsonl")
    with open(out_team, "w", encoding="utf-8") as f:
        for t in teams:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"Extracted {len(positions)} raw positions, Merged into {len(final_records)} unique entities -> {out_file}")
    print(f"Aggregated {len(teams)} teams -> {out_team}")

if __name__ == "__main__":
    extract_positions()
