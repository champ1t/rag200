
from typing import Dict, Any, List, Optional
from src.directory.lookup import lookup_phones
from src.directory.format_answer import format_contact_answer

class ContactHandler:
    """
    Handles queries for Phone Numbers, Emails, and Contact Information.
    Replaces direct calls to `lookup_phones`.
    """
    
    TRIGGERS = [
        "เบอร์์", "เบอร์", "โทร", "ติดต่อ", "email", "อีเมล", "fax", "ที่อยู่", 
        "เบอ", "เบอร", "โท", "บอร์", "ขอ", "ของ", "phone", "โทรศัพท์", "เบอร์โทร",
        "เบอร์โทรศัพท์", "เบอร์ของ", "ขอเบอร์", "รบกวนขอ", "หาเบอร์", "โทรหา", "โทรไป", "คุยกับ"
    ]
    
    POLITE_PARTICLES = [
        "ครับ", "ค่ะ", "krup", "ka", "หน่อย", "ด้วยครับ", "ขอ", "รบกวน", "ช่วย", 
        "อยากทราบ", "query", "search", "ตอบ", "บอก", "คือ", "อะไร", "ไหน", 
        "ที่ไหน", "สอบถาม", "ถาม", "ใคร", "คนไหน", "เอ๊ะ", "แล้ว", "หล่ะ", 
        "นะ", "จ๊ะ", "จ้า", "สิ", "ที", "หน่อยดิ", "ป่าว", "ไหม", "จุง", "เลย", 
        "น้า", "พี่", "จะ", "หา", "ต้อง", "อยาก", "ได้", "มี", "เอา", "ตรงไหน",
        "ชื่อ", "ว่า", "เนี่ย", "น่ะ", "จ้ะ", "จ๋า", "ด้วย", "ครับผม", "ค่ะคุณ"
    ]

    # Phase 221: Confidence Constants
    HIGH_CONFIDENCE_THRESHOLD = 80
    MEDIUM_CONFIDENCE_THRESHOLD = 40
    CLOSE_MATCH_DIFF = 15
    
    @classmethod
    def is_match(cls, query: str) -> bool:
        q_lower = query.lower()
        return any(k in q_lower for k in cls.TRIGGERS)

    @staticmethod
    def classify_contact_query(q_clean: str) -> str:
        """
        Classify query intent type: TEAM | PERSON | ROLE | UNKNOWN
        """
        # 1. Team Patterns
        team_triggers = ["งาน", "ศูนย์", "ส่วน", "ฝ่าย", "กอง", "แผนก", "section", "department", "team"]
        if any(t in q_clean for t in team_triggers):
            return "TEAM"
            
        # 2. Role Patterns
        # Check strict role keys (e.g. ผส. xxx, ผจ. xxx)
        # We need to distinguish "ผส" (Role) from "สมชาย" (Person)
        role_prefixes = ["ผส.", "ผจ.", "ผอ.", "ชจญ.", "หน.", "หัวหน้า"]
        if any(p in q_clean for p in role_prefixes):
            return "ROLE"
            
        # Also check for non-dotted variants if they start with typical role tokens
        if any(q_clean.startswith(p) for p in ["ผส", "ผจ", "ผอ", "ชจญ"]):
            return "ROLE"
            
        # 3. Person Patterns
        # Thai titles
        person_titles = ["คุณ", "นาย", "นาง", "น.ส.", "ว่าที่"]
        if any(t in q_clean for t in person_titles):
            return "PERSON"
            
        return "UNKNOWN"

    @classmethod
    def handle(cls, query: str, records: List[Dict[str, Any]], directory_handler: Optional[Any] = None, llm_cfg: Optional[Dict] = None, disambiguation_state: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Lookup contact info with Strict Priority & Assistant Persona (Phase 221).
        """
        from src.utils.normalization import normalize_text, insert_thai_english_spacing, strip_contact_noise
        
        # Phase 221: Disambiguation Check
        # Rule 1: Treat as NEW query unless explicit reply
        selected_candidate = None
        
        if disambiguation_state:
            choices = disambiguation_state.get("choices", [])
            # check if query is explicit selection
            # 1. Number match (1, 2)
            try:
                idx = int(query.strip()) - 1
                if 0 <= idx < len(choices):
                    selected_candidate = choices[idx]
            except ValueError:
                pass
                
            # 2. Name match (fuzzy)
            if not selected_candidate:
                q_norm = normalize_text(query)
                for c in choices:
                    if q_norm == normalize_text(c.get("name", "")):
                        selected_candidate = c
                        break
            
            # If selected, skip search and generate HIT
            if selected_candidate:
                print(f"[ContactHandler] Disambiguation Selected: {selected_candidate.get('name')}")
                # Generate HIT response via LLM directly
                return cls._generate_llm_response(query, [selected_candidate], llm_cfg, route="contact_hit_disambiguated")
        
        # --- Normal Search Flow ---
        
        # Phase 100: Spacing Fix (Thai-English)
        query = insert_thai_english_spacing(query)
        
        # Phase 100+: Typo Fix (Leading vowels) & Hyphens
        from src.utils.normalization import remove_leading_combining_marks, normalize_hyphens, ROLE_ALIASES, UNIT_ALIASES
        query = remove_leading_combining_marks(query)
        query = normalize_hyphens(query)
        
        q_lower = query.lower()
        q_clean = q_lower
        
        # Strip functional triggers
        for t in cls.TRIGGERS:
            q_clean = q_clean.replace(t, " ")
            
        # Strip polite particles
        sorted_particles = sorted(cls.POLITE_PARTICLES, key=len, reverse=True)
        for p in sorted_particles:
             q_clean = q_clean.replace(p, " ")
             
        q_clean = normalize_text(q_clean)
        
        # Apply Aliases
        for k, v in ROLE_ALIASES.items():
            k_norm = normalize_text(k)
            if k_norm in q_clean.split():
                 q_clean = q_clean.replace(k_norm, v.lower())
            elif k_norm == q_clean:
                 q_clean = v.lower()

        for k, v in UNIT_ALIASES.items():
            k_norm = normalize_text(k)
            if k_norm in q_clean.split():
                 q_clean = q_clean.replace(k_norm, v.lower())
            elif k_norm in q_clean: 
                 q_clean = q_clean.replace(k_norm, v.lower())

        from src.utils.normalization import PROVINCE_ALIASES
        for k, v in PROVINCE_ALIASES.items():
             if k in q_clean:
                 q_clean = q_clean.replace(k, v)

        intent_type = cls.classify_contact_query(q_clean)
        print(f"[DEBUG Contact] Query: '{q_clean}', Intent: {intent_type}")
        
        hits = []
        source_type = "generic"
        
        # --- Strategy ---
        if intent_type == "TEAM":
            q_stripped = strip_contact_noise(q_clean)
            team_hits = lookup_phones(q_stripped, records)
            team_hits = [r for r in team_hits if r.get("type") == "team"]
            
            if team_hits:
                hits = team_hits
                source_type = "team"
            elif directory_handler:
                role_hits = directory_handler.find_by_role(q_clean)
                if role_hits:
                    hits = role_hits
                    source_type = "role_group"
                    
        elif intent_type == "PERSON":
            if directory_handler:
                person_hits = directory_handler.find_person(q_clean)
                if person_hits:
                    hits = person_hits
                    source_type = "person_strict"
            
            if not hits: 
                hits = lookup_phones(query, records)
                if hits: source_type = "contact_book_person"

        elif intent_type == "ROLE":
            if len(q_clean) < 4:
                 suggestions = directory_handler.suggest_roles(q_clean) if directory_handler else []
                 # LLM can handle "Miss" with hints, but passing empty hits + suggestions might be better
                 # For now, treat as Miss
                 hits = []
            else:
                 if directory_handler:
                    role_hits = directory_handler.find_by_role(q_clean)
                    if role_hits:
                        hits = role_hits
                        source_type = "role"

        elif intent_type == "UNKNOWN":
             if len(q_clean) < 5 and directory_handler:
                 # Check Role Suggestion
                 pass # Treat as miss/ambiguous

             q_stripped = strip_contact_noise(q_clean) if len(q_clean) > 3 else q_clean
             hits = lookup_phones(q_stripped, records)
             if hits: source_type = "contact_book_fuzzy"
             
             if not hits:
                import re
                from src.directory.lookup import lookup_by_phone
                digits = re.sub(r"\D", "", query)
                if len(digits) >= 4:
                    hits = lookup_by_phone(query, records)
                    if hits: source_type = "reverse"
        
        # Location Filtering (Phase R7)
        from src.utils.section_filter import extract_location_intent
        target_locations = extract_location_intent(query)
        if target_locations and hits:
            filtered_hits = []
            for h in hits:
                h_text = (h.get("name", "") + " " + str(h.get("role", ""))).lower()
                is_loc_match = False
                for loc in target_locations:
                    if loc in h_text:
                        is_loc_match = True
                        break
                if is_loc_match:
                    filtered_hits.append(h)
            
            if filtered_hits:
                hits = filtered_hits

        # Fallback Check (Directory Handler Fallback)
        if not hits and top_score_check(hits) < 40: # Helper needed or check inline
             if directory_handler:
                 fallback_res = directory_handler.handle_team_lookup(q_clean)
                 if fallback_res and fallback_res.get("hits"):
                     hits = fallback_res["hits"]
                     # Inject High Score (100) and Role (Team Name)
                     for h in hits: 
                         h["_score"] = 100
                         if not h.get("role"):
                             h["role"] = q_clean.title() # Use query as role for context
        
        # Initialize outcome and route (will be overridden by Step 19.5 if applicable)
        outcome = "UNKNOWN"
        route = f"contact_hit_{source_type}"
        
        # ========================================================================
        # STEP 19.5: Progressive Prefix Suggestion (UNIVERSAL HOOK)
        # CRITICAL: Execute BEFORE any miss routing to cover ALL query paths
        # ========================================================================
        if not hits and directory_handler and len(q_clean) >= 4:
            print(f"[STEP 19.5 UNIVERSAL] Checking for prefix matches in '{q_clean}'")
            prefix_teams = []
            
            # STEP 19.5 Improvement: More aggressive stripping for prefix matching
            from src.directory.lookup import strip_query
            
            # Prepare query variants for prefix match
            queries_to_try = [q_clean.strip()]
            
            # 1. Strip common generic words
            q_no_generic = q_clean.strip()
            for generic_word in ["ศูนย์", "ฝ่าย", "แผนก", "หน่วย", "งาน", "ทีม", "กลุ่ม", "ส่วน", "กอง"]:
                q_no_generic = q_no_generic.replace(generic_word, "").strip()
            if q_no_generic and q_no_generic != q_clean.strip():
                queries_to_try.append(q_no_generic)
            
            # 2. Extract potential technical entites (Latin/Numbers)
            import re
            latin_parts = re.findall(r'[a-z0-9\-]{3,}', q_clean)
            for part in latin_parts:
                if part not in queries_to_try:
                    queries_to_try.append(part)
            
            # 3. Aggressive Thai strip (Try to find the "noun" among "verbs")
            # If query is long, try stripping words from the edges
            if len(q_clean.split()) > 2:
                q_words = q_clean.split()
                # Try middle word if it looks like an entity
                for w in q_words:
                    if len(w) >= 3 and w not in queries_to_try:
                        queries_to_try.append(w)

            print(f"[DEBUG] [STEP 19.5] Queries to try: {queries_to_try}")
            
            # Search RECORDS
            for q_check in queries_to_try:
                if prefix_teams: break
                
                print(f"[PREFIX MATCH] Trying '{q_check}' in records")
                # Normalize for matching
                q_match = q_check.replace("ศูนย์", "").replace("บริการ", "").replace("ลูกค้า", "").strip().lower()
                if len(q_match) < 2: continue

                for record in records:
                    record_name = record.get("name", "").lower()
                    record_unit = str(record.get("unit", "")).lower()
                    
                    name_norm = record_name.replace("ศูนย์", "").replace("บริการ", "").replace("ลูกค้า", "").strip()
                    unit_norm = record_unit.replace("ศูนย์", "").replace("บริการ", "").replace("ลูกค้า", "").strip()
                    
                    match = False
                    # Strategy: Substring or Word Prefix
                    if q_match in name_norm or q_match in unit_norm:
                        match = True
                    else:
                        for word in (record_name + " " + record_unit).split():
                            if word.startswith(q_match):
                                match = True; break
                    
                    if match:
                        record_copy = record.copy()
                        record_copy["_score"] = 85
                        prefix_teams.append(record_copy)
                        if len(prefix_teams) >= 10: break
            
            if prefix_teams:
                print(f"[STEP 19.5 UNIVERSAL] Found {len(prefix_teams)} matches")
                prefix_teams.sort(key=lambda x: x.get("_score", 0), reverse=True)
                hits = prefix_teams[:10]
                source_type = "contact_prefix_match"
                outcome = "AMBIGUOUS"
                route = "contact_prefix_ambiguous"
        # ========================================================================
        
        # Sort by score before determining outcome
        hits.sort(key=lambda x: x.get("_score", 0), reverse=True)
        top_score = hits[0].get("_score", 0) if hits else 0

        # Phase 225: Filter Low Quality Candidates (Noise Filter)
        # Only keep candidates close to Top Score to determine true ambiguity
        if hits and top_score > 30:
             # Keep matches within range (e.g. 15 points)
             cutoff = top_score - cls.CLOSE_MATCH_DIFF 
             msg = f"[DEBUG] Filtering hits (Top={top_score}, Cutoff={cutoff})"
             hits = [h for h in hits if h.get("_score", 0) >= cutoff]
             print(f"{msg} -> Kept {len(hits)} candidates.")

        # Outcome Logic (Phase 228: Strict Rules)
        if outcome != "HIT" and outcome != "AMBIGUOUS":  # Skip if already set by Step 19.5
            outcome = "UNKNOWN"
        if "team_prefix" not in source_type:  # Skip if already set by Step 19.5
            route = f"contact_hit_{source_type}"
        
        # Rule I: Broad Query Policy
        from src.directory.lookup import is_broad_query
        is_broad = is_broad_query(q_clean)
        
        # Rule D.3: Check "All" intent
        all_intent_keywords = ["ทั้งหมด", "พิมพ์มาให้หมด", "รวม", "มีหลายอัน", "เอาทุกอัน"]
        force_all = any(k in query for k in all_intent_keywords) or is_broad
        
        if not hits:
            # STEP 19.3: Level 3 - Prefix/Partial Match (Domain-Scoped)
            # Before declaring MISS, try prefix matching for short queries
            if len(q_clean) <= 6:  # Threshold for "short query"
                print(f"[DEBUG] [STEP 19.3] No exact/fuzzy match. Trying prefix match for '{q_clean}'")
                prefix_hits = []
                q_prefix = q_clean.strip()
                
                for record in records:
                    record_name = record.get("name", "").lower()
                    record_role = str(record.get("role", "")).lower()
                    record_unit = str(record.get("unit", "")).lower()
                    
                    if (q_prefix in record_name or q_prefix in record_role or q_prefix in record_unit):
                        if record_name.startswith(q_prefix):
                            record["_score"] = 90
                        elif q_prefix in record_name:
                            record["_score"] = 75
                        else:
                            record["_score"] = 60
                        prefix_hits.append(record)
                
                if prefix_hits:
                    print(f"[DEBUG] [STEP 19.3] Found {len(prefix_hits)} prefix matches -> Selection mode")
                    prefix_hits.sort(key=lambda x: x.get("_score", 0), reverse=True)
                    hits = prefix_hits[:10]
                    source_type = "contact_prefix_match"
                    outcome = "AMBIGUOUS"
                    route = "contact_prefix_ambiguous"
            
            if not hits:
                outcome = "MISS"
                route = "contact_miss_strict"
            
                # Phase 236: Helpful Broad Miss (Rule BR-2)
                from src.directory.lookup import VENDOR_CONTACTS
                if is_broad and q_clean in VENDOR_CONTACTS:
                    return {
                        "answer": f"ไม่พบข้อมูลเบอร์โทรศัพท์ '{q_clean}' โดยตรง\n\nคำแนะนำ: {VENDOR_CONTACTS[q_clean]}",
                        "route": "contact_miss_broad_help",
                        "context": ""
                    }

                # STEP 19.4: Domain Isolation Guard - NO global suggestions
                return {
                    "answer": "ไม่พบข้อมูลในฐานข้อมูลติดต่อ\n\n(ลองระบุ ชื่อหน่วยงานเต็ม หรือ จังหวัด เพิ่มเติม)",
                    "route": "contact_miss_domain_strict",
                    "context": ""
                }
            

        if len(hits) == 1:
            outcome = "HIT"
        elif source_type.startswith("team_prefix"):
            # Step 19.5 Output Handling: Keep existing outcome/route
            # e.g. team_prefix_auto (Hit but many members) or team_prefix_ambiguous
            pass
        else:
            # len(hits) > 1
            if force_all:
                route = "contact_broad_list" if is_broad else "contact_ambiguous_all"
            else:
                outcome = "AMBIGUOUS"
                route = "contact_ambiguous"

        # Final LLM Generation (or Deterministic)
        # Pass all hits if force_all, else top 6 (handled in generate_llm logic via limit check?)
        # Actually generate_llm slicing happens later. We should pass full hits if force_all.
        
        top_hits = hits if force_all else hits[:10] # Pass more for ambiguity check
        
        return cls._generate_llm_response(query, top_hits, llm_cfg, route=route)

    @classmethod
    def _generate_llm_response(cls, query: str, candidates: List[Dict], llm_cfg: Optional[Dict], route: str) -> Dict[str, Any]:
        """
        Calls LLM with TEMPLATE_CONTACT to generate final answer.
        """
        if not llm_cfg:
             # Fallback if no LLM config (should not happen in prod)
             return {"answer": "LLM Config Missing", "route": "error", "hits": candidates}
             
        from src.rag.prompts import TEMPLATE_CONTACT
        from src.rag.ollama_client import ollama_generate
        import json
        
        # Robust serializer for sets and non-serializable objects
        def json_default(o):
            if isinstance(o, set):
                return list(o)
            return str(o)
        
        # Helper to strict set (remove large fields)
        def sanitize(c_list):
            out = []
            for c in c_list:
                d = dict(c)
                # Remove internal sets or large fields
                d.pop("tokens", None)
                d.pop("latin_tokens", None)
                d.pop("alias_set", None)
                d.pop("_precomputed", None)
                out.append(d)
            return out
        
        # Prepare Candidate JSON for Prompt
        # Phase 226: Deterministic Contact Rendering (No LLM)
        from src.directory.format_answer import format_contact_answer, format_candidate_list
        
        # 0) FILTERED MISS
        if not candidates: 
            # Rule G: Failure Mode with Suggestions
            from src.directory.lookup import generate_suggestions
            # We don't have records here... wait, handle() has records, but _generate_llm_response doesn't.
            # We need to pass records or suggestions to _generate_llm_response?
            # Better to handle this logic in handle() before calling this.
            # Refactoring... see below.
            
            return {
                "answer": (
                    "ไม่พบข้อมูลเบอร์โทรศัพท์ที่ระบุโดยตรง\n"
                    "ช่วยระบุเพิ่ม 1 อย่าง: (ชื่อบุคคล / ชื่อหน่วยงานเต็ม / จังหวัด/พื้นที่ / ตัวย่อที่ถูกต้อง)"
                ),
                "route": "contact_miss_strict",
                "context": "" # No context for miss
            }
            
        # 1) SINGLE HIT
        if len(candidates) == 1:
            best = candidates[0]
            ans = format_contact_answer(query, best.get("phones", []), best)
            return {
                "answer": ans,
                "route": route, 
                "context": json.dumps(sanitize([best]), ensure_ascii=False, default=json_default),
                "hits": [best]
            }
            
        # 2) AMBIGUOUS
        # Rule D.1: If many matches but broad query -> List ALL (max reasonable)
        # Rule D.3: If user says "ทั้งหมด", list ALL.
        
        # Check "All" intent (passed via route?)
        limit = 10
        contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False, default=json_default)
        
        if route == "contact_ambiguous_all":
            limit = 50 # Max limit for "All"
            contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False, default=json_default)
        elif route == "contact_broad_list":
            limit = 50
            # Phase 235: Enable context for broad lists to allow selection (Fix "2" failure)
            contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False, default=json_default)

        ans = format_candidate_list(candidates, max_items=limit)
        
        # Step 19.5: Allow special routes to pass through (don't force contact_ambiguous)
        preserve_routes = ["contact_broad_list", "contact_hit_team_auto", "contact_prefix_ambiguous", "contact_ambiguous_all"]
        final_route = route if route in preserve_routes else "contact_ambiguous"
        
        return {
            "answer": ans,
            "route": final_route,
            "context": contact_context,
            # Return all candidates (or limited?) as hits for processing
            "hits": candidates[:limit]
        }
        # The original code had a try-except block here, but the new instruction
        # seems to replace the entire LLM call logic, including the try block.
        # The `print(f"[ContactHandler] LLM Error: {e}")` and subsequent return
        # were part of the `except` block. Since the LLM call is removed,
        # this part is also removed as per the instruction.
        # If an error handling for the new deterministic logic is needed,
        # it should be added explicitly.

def top_score_check(hits):
    if not hits: return 0
    return hits[0].get("_score", 0)
