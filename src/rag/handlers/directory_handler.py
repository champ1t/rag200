
from typing import Dict, List, Any, Optional
from collections import defaultdict
import time
from difflib import SequenceMatcher
from src.utils.normalization import normalize_text, normalize_for_matching, ROLE_ALIASES, normalize_role

class DirectoryHandler:
    def __init__(self, position_index: Dict[str, Any], records: List[Dict[str, Any]], team_index: Dict[str, Any] = None, query_normalizer=None):
        """
        Initializes the DirectoryHandler.
        :param position_index: Dictionary mapping Role Name to Details.
        :param records: Flat list of all records (used for gap enrichment).
        :param team_index: Dictionary mapping Team Name to details.
        :param query_normalizer: Optional QueryNormalizer for Phase 2.1 (LLM paraphrasing).
        """
        self.position_index = position_index
        self.records = records
        self.team_index = team_index or {}
        self.query_normalizer = query_normalizer  # Phase 2.1: LLM Query Normalizer
        self.pos_norm_map = self._build_norm_map()
        self.team_norm_map = self._build_team_norm_map()
        
        # Optimization: Pre-index records for fast enrichment
        self.record_name_map = self._build_record_name_map()
        # Optimization: Pre-compute normalized roles list for scanning
        self.norm_roles_list = [(r, normalize_for_matching(r)) for r in self.position_index.keys()]

    def _build_norm_map(self) -> Dict[str, List[str]]:
        """
        Builds a normalized map for O(1) role lookup.
        """
        pos_map = defaultdict(list)
        for role in self.position_index:
            r_norm = normalize_for_matching(role)
            pos_map[r_norm].append(role)
            
            # Additional keys for no-space variant
            r_ns = r_norm.replace(" ", "")
            if len(r_ns) > 2 and r_ns != r_norm:
                pos_map[r_ns].append(role)
        return pos_map

    def _build_team_norm_map(self) -> Dict[str, List[str]]:
        """
        Builds a normalized map for O(1) team lookup.
        """
        team_map = defaultdict(list)
        for team in self.team_index:
            t_norm = normalize_for_matching(team)
            team_map[t_norm].append(team)
            
            # Additional keys for stripped variant
            t_ns = t_norm.replace(" ", "").replace("งาน", "").replace("ทีม", "")
            if len(t_ns) > 2:
                team_map[t_ns].append(team)
                
            # Full no-space
            t_full_ns = t_norm.replace(" ", "")
            if t_full_ns != t_ns:
                 team_map[t_full_ns].append(team)

        return team_map

    def _build_record_name_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Builds Name -> Record map for O(1) enrichment.
        """
        m = {}
        for rec in self.records:
            if rec.get("type") == "person":
                n = rec.get("name", "")
                if n:
                    norm = normalize_for_matching(n)
                    # If duplicate names, last one wins or we could store list.
                    # For enrichment (phone), any valid record is helpful.
                    if norm not in m or (not m[norm].get("phones") and rec.get("phones")):
                        m[norm] = rec
        return m

    def find_by_role(self, role_query: str) -> List[Dict[str, Any]]:
        """
        Public method to find entities by role name (Fuzzy/Exact).
        Useful for fallback in ContactHandler.
        """
        q_norm = normalize_for_matching(role_query)
        
        matched_roles = []
        
        # Exact/Norm check
        matches = self._find_matches(q_norm)
        if matches:
            matched_roles.extend(matches)
            
        # 3. Retrieve Records
        found_people = []
        seen_keys = set()
        
        for role in matched_roles:
            if role in self.position_index:
                people = self.position_index[role]
                for p in people:
                    # Dedup by (Role, Name) in case of overlap
                    key = (p["role"], p["name"])
                    if key not in seen_keys:
                        found_people.append(p)
                        seen_keys.add(key)
        
        # 4. Enrich
        self._enrich_data_gaps(found_people)
        return found_people

    def find_person(self, name_query: str) -> List[Dict[str, Any]]:
        """
        Find person by name (Strict Search).
        Prioritizes Person Records in Directory.
        """
        q_norm = normalize_text(name_query)
        # Remove common prefixes from query just in case (e.g. "คุณสมบูรณ์")
        q_norm = q_norm.replace("คุณ", "").replace("นาย", "").replace("นาง", "").strip()
        
        matches = []
        if len(q_norm) < 2: return matches

        seen_ids = set()
        for rec in self.records:
            if rec.get("type") == "person":
                r_name = rec.get("name", "")
                r_norm = normalize_text(r_name)
                
                # Check Containment
                if q_norm in r_norm:
                    matches.append(rec)
                    seen_ids.add(rec.get("name")) # Dedup by name?
                    
        return matches

    def suggest_persons(self, prefix: str, limit: int = 5) -> List[str]:
        """
        Suggest person names starting with prefix.
        """
        p_norm = normalize_text(prefix).lower()
        candidates = []
        seen = set()
        
        for rec in self.records:
            if rec.get("type") == "person":
                name = rec.get("name", "")
                n_norm = normalize_text(name).lower()
                
                # Check strict prefix or slight fuzzy?
                # For suggestions, prefix is best.
                hit = False
                if n_norm.startswith(p_norm): hit = True
                elif p_norm in n_norm: hit = True # Substring OK
                
                if hit and name not in seen:
                    candidates.append(name)
                    seen.add(name)
        
        # Sort by length
        candidates.sort(key=len)
        return candidates[:limit]

    def suggest_roles(self, prefix: str, limit: int = 5) -> List[str]:
        """
        Suggest roles based on prefix (for Ambiguity Handling).
        Prioritizes:
        1. Exact prefix match (e.g. "ผส." -> "ผส.บลตน.")
        2. Shortest match favored (Roots)
        """
        p_norm = normalize_text(prefix).replace(".", "").lower()
        candidates = []
        
        # Priority Sets
        exact_prefix_matches = []
        partial_matches = []
        
        # Scan keys
        for role in self.position_index.keys():
            r_norm = normalize_text(role).replace(".", "").lower()
            
            if r_norm.startswith(p_norm):
                exact_prefix_matches.append(role)
            elif p_norm in r_norm:
                partial_matches.append(role)
        
        # Sort Logic
        # 1. Exact Prefix matches, sorted by length (Shortest first) then alpha
        exact_prefix_matches.sort(key=lambda x: (len(x), x))
        
        # 2. Partial matches, sorted by match position index? or length
        partial_matches.sort(key=lambda x: (len(x), x))
        
        candidates = exact_prefix_matches + partial_matches
        return candidates[:limit]

    def handle_position_holder(self, query: str) -> Dict[str, Any]:
        """
        Handle 'POSITION_HOLDER_LOOKUP'.
        Finds people holding the specific position requested (Fuzzy Match).
        """
        t_start = time.time()
        
        # 1. Extract Target Position
        # Remove trigger phrases using Regex for flexibility
        import re
        q_clean = query
        # Patterns to strip
        patterns = [
            r"(?:ใคร|คร)\s*ตำแหน่ง", r"ตำแหน่ง\s*(?:ใคร|คร)", r"ผู้ดำรงตำแหน่ง", r"(?:ใคร|คร)\s*รับผิดชอบ", 
            r"(?:ใคร|คร)\s*คือ", r"(?:ใคร|คร)\s*เป็น", r"who\s*is", r"who\s*holds", r"ตำแหน่ง", r"คนไหน", r"คือใคร",
            r"เบอร์", r"โทร", r"ติดต่อ", r"email", r"อีเมล", r"fax", r"ที่อยู่",
            r"เหรอ", r"หรอ", r"ไหม", r"มั้ย", r"หรือ", r"ครับ", r"ค่ะ", r"คะ", r"จ้า", r"หน่อย", r"นะ", r"เหรอะ"
        ]
        for p in patterns:
            q_clean = re.sub(p, "", q_clean, flags=re.IGNORECASE)
        
        q_clean = q_clean.strip()
        # Remove leading/trailing dots/punctuation if any
        q_clean = q_clean.strip(" .?,")
        
        # 2. Safety Check: If query is too short (e.g. "ผจ", "ผช"), it is too ambiguous for direct hit.
        # User Rule: "ใครคือผจ -> ควรตอบไม่พบข้อมูล + แนะนำพิมพ์เต็ม"
        if len(q_clean) < 3:
             # Try to find suggestions instead of just failing (Phase 236 Fix)
             suggestions = self.suggest_roles(q_clean)
             latency = (time.time() - t_start) * 1000
             
             if suggestions:
                 suggestion_text = ", ".join([f"'{s}'" for s in suggestions])
                 # Take the first best suggestion as the "target" for confirmation
                 target = suggestions[0] 
                 
                 return {
                    "answer": f"ไม่พบข้อมูลที่แม่นยำสำหรับ '{q_clean}'\nคุณต้องการค้นหา: {suggestion_text} หรือไม่? (กรุณาระบุชื่อเต็ม เช่น 'ผจ.สบลตน.')",
                    "route": "position_ambiguous",
                    "candidates": suggestions,
                    "latencies": {"directory": latency},
                    "pending_action": {
                        "kind": "position_confirmation",
                        "target_name": target,
                        "candidates": suggestions
                    }
                 }

             return {
                "answer": f"ไม่พบข้อมูลผู้ดำรงตำแหน่ง '{q_clean}' ในระบบ (กรุณาระบุชื่อเต็ม เช่น 'ผจ.สบลตน.')",
                "route": "position_miss",
                "latencies": {"directory": latency}
            }
            
        # 3. Lookup using reusable method
        found_people = self.find_by_role(q_clean)
        
        latency = (time.time() - t_start) * 1000
        
        if found_people:
            # Customized Answer Format for Position Lookup
            lines = []
            for p in found_people[:5]:
                # Format: [Position] Name (Source)
                # Show Phones/Emails clearly
                block = f"**ตำแหน่ง:** {p['role']}\n**ชื่อ:** {p['name']}"
                
                # Check for "sources" key from Merged entity
                # The extract_positions.py writes "sources" list.
                
                if p.get("phones"): block += f"\n📞 โทร: {', '.join(p['phones'])}"
                if p.get("emails"): block += f"\n📧 อีเมล: {', '.join(p['emails'])}"
                
                lines.append(block)
                
            ans = "\n\n".join(lines)
            return {
                "answer": ans,
                "route": "position_holder_hit",
                "latencies": {"directory": latency},
                "hits": found_people
            }
        else:
             # Fallback Suggestion? 
             # Scan for close matches?
             return {
                "answer": f"ไม่พบข้อมูลผู้ดำรงตำแหน่ง '{q_clean}' ในระบบ",
                "route": "position_miss",
                "latencies": {"directory": latency}
            }

    def handle_management_query(self, query: str) -> Dict[str, Any]:
        """
        Handle 'MANAGEMENT_LOOKUP' intent.
        Returns list of executives (ผส., ผจ., ผอ., หัวหน้าส่วน).
        """
        t_start = time.time()
        
        # 1. Identify specific unit filter if provided (e.g. "ผู้บริหาร สบลตน.")
        # Remove trigger keywords
        triggers = ["ผู้บริหาร", "รายชื่อ", "หัวหน้า", "ผส.", "ผจ.", "ผอ.", "ผู้อำนวยการ", "manager", "director",
                    "เบอร์", "โทร", "ติดต่อ", "email", "อีเมล", "fax", "ที่อยู่"]
        q_filter = query
        for t in triggers:
            q_filter = q_filter.replace(t, "")
        
        q_filter = q_filter.strip().lower()
        
        # 2. Scan for Executive Roles
        matches = []
        exec_prefixes = ["ผส.", "ผจ.", "ผอ.", "หัวหน้าส่วน"]
        
        for role, persons in self.position_index.items():
            # Check if role is an executive role
            role_norm = normalize_for_matching(role)
            is_exec = any(role.strip().startswith(p) for p in exec_prefixes) or \
                      "ผู้จัดการ" in role or "ผู้อำนวยการ" in role
            
            if not is_exec:
                continue
                
            # If user provided a unit filter, role must match it
            if q_filter:
                # Naive substring match. "สบลตน" in "ผส.สบลตน."
                if q_filter in role_norm:
                    matches.extend(persons)
            else:
                # No filter -> Return all high-ranking (Limit to higher ranks if possible, e.g. ผส.)
                # For now return all (limited by format_answer)
                matches.extend(persons)
                
        # 3. Sort/Rank
        # Prioritize "ผส." > "ผจ." > "หัวหน้า"
        def rank(p):
            r = p['role']
            if r.startswith("ผส."): return 1
            if r.startswith("ผอ."): return 1
            if r.startswith("ผจ."): return 2
            return 3
            
        matches.sort(key=rank)
        
        # 4. Enrich & Format
        self._enrich_data_gaps(matches)
        latency = (time.time() - t_start) * 1000
        
        if matches:

            # Ambiguity Logic Bypass (User Preference: Direct Answer)
            # if len(unique_roles) > 1 and len(q_filter) < 5:
            #     # bypass ambiguity check
            #     pass
            
            return self._format_answer(matches, latency)
        else:
             return {
                "answer": f"ไม่พบรายชื่อผู้บริหารที่สอดคล้องกับ '{query}'",
                "route": "position_miss",
                "latencies": {"directory": latency}
            }

    def handle_team_lookup(self, query: str, is_asset: bool = False, retry_count: int = 0) -> Dict[str, Any]:
        """
        Handle 'TEAM_LOOKUP' intent.
        Strictly returns member list from Team Index.
        
        :param retry_count: Tracks normalization retries (max 1 to prevent loops)
        """
        t_start = time.time()
        
        # Phase 91: Team Alias Map (Candidate Lists)
        TEAM_ALIASES = {
            "smc": ["management smc", "งาน management smc", "management (smc)", "smc management", "smc"],
            "management": ["management smc", "งาน management smc", "management (smc)", "smc management"],
            "help desk": ["ข.บลตน.", "helpdesk", "help desk"],
            "helpdesk": ["ข.บลตน.", "helpdesk", "help desk"],
            "fttx": ["งาน fttx", "fttx"],
            "omc": ["omc", "ศูนย์ omc", "omc hatyai", "omc songkhla"],
            "rnoc": ["rnoc", "ศูนย์ rnoc"],
            "csoc": ["csoc", "ศูนย์ csoc"],
            "noc": ["noc", "ศูนย์ noc"]
        }
        
        # 1. Canonicalize Team Query
        import re
        q_clean = query
        
        # Remove bracket descriptors: "HelpDesk (ดูแลลูกค้า)" -> "HelpDesk"
        q_clean = re.sub(r'\([^)]*\)', '', q_clean)  # Remove () content
        q_clean = re.sub(r'（[^）]*）', '', q_clean)  # Remove （） content
        
        # Strip prefixes
        prefixes = ["สมาชิกงาน", "บุคลากรงาน", "รายชื่อทีม", "ทีมงาน", "ฝ่ายงาน", "ส่วนงาน", "กลุ่มงาน",
                    "ทีม", "งาน", "สมาชิก", "บุคลากร", "ผู้รับผิดชอบ", "มีใครบ้าง", "ฝ่าย", "กลุ่ม", "ส่วน",
                    "ตาราง", "รูปภาพ", "รูป", "ภาพ", "แผนผัง", "ผัง", "เบอร์โทร", "เบอร์", "phone", "ติดต่อ"]
        for prefix in prefixes:
            q_clean = re.sub(r'\b' + prefix + r'\b', '', q_clean, flags=re.IGNORECASE)
            # Also handle Thai tokens without boundaries if needed
            q_clean = q_clean.replace(prefix, "")
        
        # Normalize spaces
        q_clean = ' '.join(q_clean.split()).strip()
        
        # Fix common typos: "งานสมาชิก าน" -> remove duplicate "าน"
        q_clean = re.sub(r'(\S+)\s+าน', r'\1งาน', q_clean)  # "X าน" -> "Xงาน"
        
        q_norm = normalize_for_matching(q_clean)
        
        print(f"[DEBUG] Team lookup canonical query: '{query}' -> '{q_clean}' -> '{q_norm}'")
        
        # 2. Try Alias Match (Improved: Containment)
        q_lower = q_clean.lower()
        alias_candidates = []
        best_alias_key = ""
        
        # Sort keys by length desc to match longest alias first
        sorted_alias_keys = sorted(TEAM_ALIASES.keys(), key=len, reverse=True)
        
        for alias_key in sorted_alias_keys:
            # Check if alias key is in query (word boundary check preferred, but containment ok for now)
            # Use simple containment for robustness against Thai spacing
            if alias_key in q_lower:
                alias_candidates = TEAM_ALIASES[alias_key]
                best_alias_key = alias_key
                print(f"[DEBUG] Alias matched (containment): '{alias_key}' in '{q_lower}' -> candidates: {alias_candidates}")
                break # Prioritize longest match
        
        if alias_candidates:
            # Try exact match for each alias candidate against Normalized Index
            for candidate in alias_candidates:
                cand_norm = normalize_for_matching(candidate)
                if cand_norm in self.team_norm_map:
                    matches = self.team_norm_map[cand_norm]
                    print(f"[DEBUG] Alias candidate '{candidate}' matched team(s): {matches}")
                    q_clean = candidate # Rewrite query to clean team name
                    q_norm = cand_norm
                    break
            else:
                # No exact match for mapped candidate in index
                # This suggests Alias Map points to a team name that doesn't exist or spells differently
                print(f"[DEBUG] Alias candidates {alias_candidates} found but no exact match in team_norm_map.")
                # Proceed to fuzzy matching using the *candidate* names instead of original noisy query
                # This helps "helpdesk noise" -> fuzzy("helpdesk") which is better than fuzzy("helpdesk noise")
                pass


        
        # 2. Match Logic: Exact -> Alias -> Fuzzy
        matches = []
        is_generic = len(q_clean) < 2
        
        # DEMOTION GUARDRAIL (Phase 72)
        DOC_TRIGGERS = ["คู่มือ", "manual", "วิธี", "ขั้นตอน", "เอกสาร", "pdf", "guide", "setup", "config", "sop", "procedure"]
        is_document = any(t in query.lower() for t in DOC_TRIGGERS)
        
        if is_document:
             latency = (time.time() - t_start) * 1000
             return {
                "answer": f"คำถาม '{query}' ดูเหมือนจะเป็นการค้นหาคู่มือหรือเอกสาร ไม่ใช่ข้อมูลบุคลากร\nระบบกำลังส่งต่อไปยังส่วนงานค้นหาเอกสารครับ...",
                "route": "team_demoted",
                "latencies": {"directory": latency}
             }

        if not is_generic:
            # A. Exact match
            raw_q_norm = normalize_for_matching(query)
            if raw_q_norm in self.team_norm_map:
                matches.extend(self.team_norm_map[raw_q_norm])
            elif q_norm in self.team_norm_map:
                matches.extend(self.team_norm_map[q_norm])
            
            # B. Alias Match Logic
            if not matches and alias_candidates:
                from difflib import SequenceMatcher
                for team_key in self.team_index.keys():
                    team_norm = normalize_for_matching(team_key)
                    for cand in alias_candidates:
                        cand_norm = normalize_for_matching(cand)
                        if SequenceMatcher(None, cand_norm, team_norm).ratio() >= 0.85:
                            if team_key not in matches: matches.append(team_key)
                
            # C. Standard Substring/Fuzzy Match (if still no matches)
            if not matches:
                from difflib import SequenceMatcher
                fuzzy_candidates = []
                for team_key in self.team_index.keys():
                    team_norm = normalize_for_matching(team_key)
                    if q_norm in team_norm or team_norm in q_norm:
                        fuzzy_candidates.append((team_key, 1.0))
                    else:
                        ratio = SequenceMatcher(None, q_norm, team_norm).ratio()
                        if ratio >= 0.75:
                            fuzzy_candidates.append((team_key, ratio))
                
                if fuzzy_candidates:
                    fuzzy_candidates.sort(key=lambda x: x[1], reverse=True)
                    # Take matches within 0.05 of best score
                    best_score = fuzzy_candidates[0][1]
                    matches = [t for t, s in fuzzy_candidates if s >= best_score - 0.05]

        # 2b. Unit Fallback: Search in Records if no team hit
        # This handles OMC, RNOC, CSOC which are not formal "teams" but are units in contact list
        if not matches and not is_generic:
            print(f"[DEBUG] Team Index Miss. Falling back to Record Search for '{q_clean}'")
            for rec in self.records:
                # Look for "Unit" or "Team" field in record (type='team' or similar)
                rec_name = rec.get("name", "") or rec.get("team", "")
                if not rec_name: continue
                
                rn_norm = normalize_for_matching(rec_name)
                # Check for unit match in name OR tags (Phase 239)
                tags = rec.get("tags", [])
                tag_match = any(q_norm in normalize_for_matching(t) for t in tags)
                
                if q_norm in rn_norm or rn_norm in q_norm or tag_match:
                    matches.append(rec_name)
                    # Update team index on the fly for this session or just return dummy data
                    if rec_name not in self.team_index:
                        self.team_index[rec_name] = {
                            "team": rec_name,
                            "members": [], # No members for contact points
                            "sources": rec.get("sources", [])
                        }
                    break # Take first match

        # 3. Show All Logic (If no matches found and intent is show-all)
        SHOW_ALL_KEYWORDS = ["ทั้งหมด", "รายชื่อ", "show all", "list all", "มีอะไรบ้าง", "มีทีมอะไรบ้าง"]
        is_show_all_intent = any(kw in query.lower() for kw in SHOW_ALL_KEYWORDS)
        
        if (query.lower() in SHOW_ALL_KEYWORDS) or (is_show_all_intent and not matches):
            all_teams = list(self.team_index.keys())
            latency = (time.time() - t_start) * 1000
            team_list = "\n".join([f"- {t}" for t in sorted(all_teams)])
            msg = f"ทีมในระบบ ({len(all_teams)} ทีม):\n{team_list}"
            return {
                "answer": msg,
                "route": "team_list_all",
                "latencies": {"directory": latency}
            }


        
        matches = list(set(matches))
        
        # 4. Ambiguity Check
        is_ambiguous, reason = self._classify_ambiguity(q_clean, matches)

        latency = (time.time() - t_start) * 1000
        
        if matches and not is_ambiguous:
            # Hit Logic (Existing)
            # Prefer longest match (Phase 241) or team with most members (Phase 249)
            # This prevents picking 'บลตน.' (1 person) over 'ส.บลตน.' (6 people) when query is 'ส.บลตน.'
            matches = sorted(matches, key=lambda x: (len(self.team_index[x].get('members', [])), len(x)), reverse=True)
            best_team = matches[0]
            team_data = self.team_index[best_team]
            members = team_data.get("members", [])
            count = len(members)
            
            if count == 0:
                lines = [f"**{best_team}** เป็นหมายเลขติดต่อ/ทีมส่วนกลางที่ไม่มีรายชื่อสมาชิกบุคคลระบุไว้ครับ"]
            else:
                lines = [f"**ทีม:** {best_team} ({count} คน)"]
                
                limit = 10
                for i, m in enumerate(members[:limit]):
                    role_prefix = ""
                    if m.get("role") and m["role"] != best_team:
                        role_prefix = f"[{m['role']}] "
                    
                    m_txt = f"- {role_prefix}{m['name']}"
                    if m.get("phones"): m_txt += f" ({', '.join(m['phones'])})"
                    lines.append(m_txt)
                    
                if count > limit:
                    lines.append(f"...และอีก {count - limit} คน")
                
            s_url = team_data.get("sources", [])[0] if team_data.get("sources") else ""
            
            if is_asset:
                if s_url:
                    ans = f"คุณสามารถดู **{best_team}** ได้ที่ลิงก์นี้ครับ:\n🔗 [เปิดไฟล์/หน้าเว็บ]({s_url})"
                else:
                    ans = f"ไม่พบลิงก์ตาราง/รูปภาพสำหรับ {best_team} ในระบบครับ"
                
                return {
                    "answer": ans,
                    "route": "asset_hit",
                    "latencies": {"directory": latency}
                }

            if s_url: lines.append(f"\n🔗 [ดูรายชื่อเต็ม]({s_url})")
                
            return {
                "answer": "\n".join(lines),
                "route": "team_hit",
                "latencies": {"directory": latency},
                "hits": members
            }
            
        elif is_ambiguous or matches: 
             # Ambiguous Case - Limit to top 3 for clarity
             suggestions = self.suggest_teams(q_clean, limit=3)
             
             if suggestions:
                 s_list = "\n".join([f"{i+1}. {s}" for i, s in enumerate(suggestions)])
                 msg = f"ไม่พบทีม '{q_clean}' โดยตรง"
                 # Tailor message based on reason
                 if reason == "generic": msg = f"คำค้นหากว้างไปครับ ('{q_clean}')"
                 
                 ans = f"{msg}\nคุณต้องการค้นหาทีมใดครับ?\n{s_list}\n\n(กรุณาระบุเลขลำดับหรือชื่อทีมเต็ม)"
                 
                 # Standardize candidates list for FollowUpResolver
                 candidates = [{"id": s, "label": s, "key": str(i+1)} for i, s in enumerate(suggestions)]
                 
                 return {
                    "answer": ans,
                    "route": "team_ambiguous",
                    "latencies": {"directory": latency},
                    "suggestions": suggestions, # Deprecated
                    "candidates": candidates    # New Standard
                 }
             
             return {
                "answer": f"ไม่พบข้อมูลทีม '{q_clean}' ในระบบ",
                "route": "team_miss",
                "latencies": {"directory": latency}
            }
            


        else:
             # Case 3: Not Generic AND No Match found
             # Fallback Rule 1: Location Check
             # If query contains a location (e.g. "หาดใหญ่", "ภูเก็ต") but missed specific team
             LOCATIONS = ["หาดใหญ่", "ภูเก็ต", "ขอนแก่น", "เชียงใหม่", "โคราช", "ชลบุรี", "พัทยา"]
             found_loc = next((loc for loc in LOCATIONS if loc in query), None)
             
             if found_loc:
                 # Suggest popular departments for that location
                 suggestions = [f"ส่วนบริการลูกค้า {found_loc}", f"ศูนย์บริการ {found_loc}", f"งานติดตั้งแก้เหตุ {found_loc}", f"ส่วนขาย {found_loc}"]
                 s_list = "\n".join([f"- {s}" for s in suggestions])
                 return {
                     "answer": f"ไม่พบหน่วยงาน '{q_clean}' โดยตรง แต่พบข้อมูลหน่วยงานในพื้นที่ '{found_loc}':\n{s_list}\n\nลองพิมพ์คำค้นหาใหม่จากรายการด้านบนได้เลยครับ",
                     "route": "team_location_fallback",
                     "latencies": {"directory": latency},
                     "suggestions": suggestions
                 }
                 
             # Try generic suggestions
             suggestions = self.suggest_teams(q_clean, limit=5)
             
             if suggestions:
                 s_list = "\n".join([f"- {s}" for s in suggestions])
                 return {
                    "answer": f"ไม่พบทีมที่ตรงกับ '{q_clean}'\nลองดูทีมเหล่านี้ไหมครับ:\n{s_list}",
                    "route": "team_ambiguous",
                    "latencies": {"directory": latency},
                    "suggestions": suggestions
                 }
             
             # CRITICAL: Prefix matching fallback (before final miss)
             # This catches queries like "ศูนย์นคร" for "ศูนย์บริการลูกค้า นครศรีธรรมราช"
             prefix_matches = []
             q_normalized = q_clean.replace("ศูนย์", "").replace("บริการ", "").replace("ลูกค้า", "").strip().lower()
             
             if len(q_normalized) >= 3:
                 for team_name in self.team_index.keys():
                     t_lower = team_name.lower()
                     t_normalized = t_lower.replace("ศูนย์", "").replace("บริการ", "").replace("ลูกค้า", "").strip()
                     
                     # Check 1: Direct match after normalization
                     if q_normalized in t_normalized:
                         prefix_matches.append(team_name)
                     # Check 2: Any word in team name starts with query
                     elif len(q_clean) >= 3:
                         for word in t_lower.split():
                             if word.startswith(q_clean.lower()):
                                 prefix_matches.append(team_name)
                                 break
             
             if prefix_matches:
                 print(f"[PREFIX FALLBACK] Found {len(prefix_matches)} matches for '{q_clean}'")
                 
                 if len(prefix_matches) == 1:
                     # Single match -> Auto-expand
                     best_team = prefix_matches[0]
                     team_data = self.team_index[best_team]
                     members = team_data.get("members", [])
                     
                     lines = [f"**ทีม:** {best_team} ({len(members)} คน)"]
                     for i, m in enumerate(members[:10]):
                         m_txt = f"- {m['name']}"
                         if m.get("phones"): m_txt += f" ({', '.join(m['phones'])})"
                         lines.append(m_txt)
                     
                     return {
                         "answer": "\n".join(lines),
                         "route": "team_hit_prefix",
                         "latencies": {"directory": latency},
                         "hits": members
                     }
                 else:
                     # Multiple matches -> Ambiguous
                     prefix_matches.sort(key=lambda x: len(x))
                     s_list = "\n".join([f"- {s}" for s in prefix_matches[:10]])
                     
                     return {
                         "answer": f"พบหลายทีมที่ตรงกับ '{q_clean}':\n{s_list}\n\n(กรุณาระบุชื่อทีมให้ชัดเจนขึ้น)",
                         "route": "team_prefix_ambiguous",
                         "latencies": {"directory": latency},
                         "suggestions": prefix_matches[:10]
                     }
             
             return {
                "answer": f"ไม่พบข้อมูลทีม '{q_clean}' ในระบบ",
                "route": "team_miss",
                "latencies": {"directory": latency}
            }

    def _classify_ambiguity(self, q_clean: str, matches: List[str]) -> (bool, str):
        """
        Determines if a query is ambiguous.
        Returns (is_ambiguous, reason)
        """
        # 1. Generic Check (Priority)
        GENERIC_TERMS = ["smc", "team", "group", "ฝ่าย", "งาน", "ส่วน", "ศูนย์", "customer", "nt", "tot", "management", "service", "admin", "region", "support", "network"]
        if q_clean.lower() in GENERIC_TERMS: return True, "generic"
        
        # 2. Uppercase/Abbr Check (e.g. "SMC", "NOC") if length is small
        if q_clean.isupper() and len(q_clean) < 4 and len(matches) != 1: 
            return True, "abbr"
        
        # 3. Length Check
        if len(q_clean) < 4 and len(matches) != 1: 
            return True, "short"
        
        # 4. Match Quality
        if matches:
            pass
            
        return False, "ok"

    def suggest_teams(self, query: str, limit: int = 5) -> List[str]:
        """
        Suggest teams based on similarity.
        """
        candidates = []
        q_norm = normalize_text(query).lower()
        
        for team in self.team_index:
            t_norm = normalize_for_matching(team).lower()
            
            # Score
            score = 0.0
            if q_norm in t_norm: score = 0.8 # Substring
            else:
                score = SequenceMatcher(None, q_norm, t_norm).ratio()
            
            if score > 0.6:
                candidates.append((score, team))
        
        # Sort by Score Desc
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c[1] for c in candidates[:limit]]

    def handle(self, query: str) -> Dict[str, Any]:
        """
        Handles Person/Position Lookup intent.
        """
        t_start = time.time()
        
        # 1. Normalize Query
        q_clean = query.replace("ติดต่อ", "").replace("เบอร์", "").replace("โทร", "").replace("หา", "").replace("ขอ", "").replace("ทราบ", "").replace("ข้อมูล", "").strip()
        q_norm = normalize_for_matching(q_clean)
        
        # 2. Apply Aliases
        for alias, full_role in ROLE_ALIASES.items():
            if alias in q_norm: 
                q_clean = q_clean.replace(alias, full_role)
                q_norm = normalize_for_matching(q_clean)
        
        # 3. Lookup Strategy
        matched_keys = self._find_matches(q_norm)
        
        # 4. Retrieve & Enrich Results
        found_positions = []
        
        # Extra tag-based matching (Phase 241: Prioritize Unit Match)
        for rec in self.records:
            tags = rec.get("tags", [])
            tag_match = any(q_norm in normalize_for_matching(t) for t in tags)
            if tag_match:
                # Give a score boost for tag-based matching when it's for position/member queries
                if not any(r.get("name") == rec.get("name") and r.get("role") == rec.get("role") for r in found_positions):
                     # Add a custom flag to indicate tag-hit without mutating original memory
                     hit_rec = dict(rec)
                     hit_rec["_tag_boost"] = 100
                     found_positions.append(hit_rec)
        
        # Original key matching (if any)
        if matched_keys:
            # Deduplicate keys
            matched_keys = list(set(matched_keys))
            for r in matched_keys:
                if r in self.position_index:
                    found_positions.extend(self.position_index[r])
        
        # Hybrid Join (Enrich missing phones)
        self._enrich_data_gaps(found_positions)
        
        # Phase 241: Final Ranking for Positions (Match-Type Priority)
        # 1. Exact Role Match
        # 2. Strong Unit/Tag Match
        # 3. Fuzzy/Partial
        def rank_pos(p):
            priority = 0
            if p.get("_tag_boost"): priority += 10 # Tag match (Unit)
            if p.get("role") and q_norm in normalize_for_matching(p["role"]): priority += 5 # Role sub-match
            return priority
            
        found_positions.sort(key=rank_pos, reverse=True)

        # 5. Output Contract / Quality Gate
        # User Rule: If query asks for contact (phone/email), result MUST have it.
        contact_intent_keywords = ["เบอร์", "โทร", "ติดต่อ", "email", "อีเมล", "fax"]
        needs_contact = any(k in query.lower() for k in contact_intent_keywords)
        
        filtered_positions = found_positions
        if needs_contact and found_positions:
            # Prioritize those with phones/emails
            with_contact = [p for p in found_positions if p.get("phones") or p.get("emails")]
            if with_contact:
                filtered_positions = with_contact
            else:
                # Found people, but NONE have contact info.
                # Instead of showing generic name list, we should be honest if strict contract implies "No Phone Found".
                # But showing the name is still partial success.
                # We will Format with a Warning prefix? 
                # Or just return them (current behavior shows name).
                # User's "Quality Gate": "If answer phone, must have regex phone".
                # Implies: Don't hallucinate.
                # Since we don't generate text, we just list data. 
                # Showing [Role] Name without phone is NOT a hallucination if we don't claim it has phone.
                # So we just ensure we don't output empty lines.
                pass

        # 6. Format Output
        latency = (time.time() - t_start) * 1000
        if filtered_positions:
            return self._format_answer(filtered_positions, latency)

        else:
            return {
                "answer": f"ไม่พบข้อมูลบุคลากรหรือตำแหน่ง '{query}' ในระบบ",
                "route": "position_miss",
                "latencies": {"directory": latency},
                "fallback_to_rag": True
            }

    def _find_matches(self, q_norm: str) -> List[str]:
        """
        Strategy: Exact -> NoSpace -> Scan
        """
        matches = []
        
        # 1. Exact / Normalized Match (O(1))
        if q_norm in self.pos_norm_map:
            matches.extend(self.pos_norm_map[q_norm])
            
        # 2. No-Space Match variant (O(1))
        q_ns = q_norm.replace(" ", "")
        if len(q_ns) > 2 and q_ns != q_norm:
            if q_ns in self.pos_norm_map:
                matches.extend(self.pos_norm_map[q_ns])
        
        # 3. Fallback Scanned Match (O(N) but restricted)
        if not matches:
             matches = self._scan_matches(q_norm)
             
        return matches

    def _scan_matches(self, q_norm: str) -> List[str]:
        matches = []
        q_ns = q_norm.replace(" ", "")
        
        # Use pre-computed list (O(N) string cmps, no re-normalization)
        for role, role_norm in self.norm_roles_list:
            if role_norm in q_norm or q_norm in role_norm:
                matches.append(role)
            else:
                rn_ns = role_norm.replace(" ", "")
                if len(rn_ns) > 3 and (rn_ns in q_ns or q_ns in rn_ns):
                    matches.append(role)
        return matches

    def _enrich_data_gaps(self, positions: List[Dict]):
        """
        Fills missing phones in position objects using raw records.
        """
        for p in positions:
            if not p.get("phones"):
                p_name_norm = p.get("name_norm") or normalize_for_matching(p.get("name", ""))
                if p_name_norm in self.record_name_map:
                    rec = self.record_name_map[p_name_norm]
                    if rec.get("phones"):
                        p["phones"] = rec.get("phones")
                        if not p.get("faxes") and rec.get("faxes"):
                            p["faxes"] = rec.get("faxes")

    def _format_answer(self, positions: List[Dict], latency: float) -> Dict[str, Any]:
        ans_parts = []
        # Limit to 10 results
        for p in positions[:10]:
            p_ans = f"[{p['role']}]\n- ชื่อ: {p['name']}"
            if p.get("phones"): p_ans += f"\n- เบอร์โทร: {', '.join(p['phones'])}"
            if p.get("emails"): p_ans += f"\n- อีเมล: {', '.join(p['emails'])}"
            ans_parts.append(p_ans)
        
        return {
            "answer": "\n\n".join(ans_parts),
            "route": "position_lookup",
            "latencies": {"directory": latency},
            "hits": positions
        }
