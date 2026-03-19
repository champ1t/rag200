
from typing import Dict, Any, List, Optional
from src.directory.lookup import lookup_phones
from src.directory.format_answer import format_contact_answer

class ContactHandler:
    """
    Handles queries for Phone Numbers, Emails, and Contact Information.
    Replaces direct calls to `lookup_phones`.
    """
    
    TRIGGERS = ["เบอร์", "โทร", "ติดต่อ", "email", "อีเมล", "fax", "ที่อยู่", "เบอ", "เบอร", "โท", "บอร์", "ขอ", "ของ", "phone"]
    
    POLITE_PARTICLES = ["ครับ", "ค่ะ", "krup", "ka", "หน่อย", "ด้วยครับ", "ขอ", "รบกวน", "ช่วย", "อยากทราบ", "query", "search"]

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
        outcome = "UNKNOWN"
        route = f"contact_hit_{source_type}"
        
        # Rule I: Broad Query Policy
        from src.directory.lookup import is_broad_query
        is_broad = is_broad_query(q_clean)
        
        # Rule D.3: Check "All" intent
        all_intent_keywords = ["ทั้งหมด", "พิมพ์มาให้หมด", "รวม", "มีหลายอัน", "เอาทุกอัน"]
        force_all = any(k in query for k in all_intent_keywords) or is_broad
        
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

            # Rule G: Failure Suggestions
            from src.directory.lookup import generate_suggestions
            suggs = generate_suggestions(q_clean, records, top_k=3)
            
            # Formulate answer here or pass to generate_llm
            # Let's handle it here for simplicity and pass as candidates? No, cleaner to return directly or use special response.
            msg = "ไม่พบข้อมูลที่ตรงกับคำค้นหา"
            if suggs:
                msg += f"\n\nหรือคุณหมายถึง:\n" + "\n".join([f"- {s}" for s in suggs])
                
            return {
                "answer": msg + "\n\n(ลองระบุ ชื่อหน่วยงาน หรือ จังหวัด เพิ่มเติม)",
                "route": "contact_miss_strict",
                "context": "" # No context
            }
            
        elif len(hits) == 1:
            outcome = "HIT"
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
        
        # Helper to strict set (sets are not serializable)
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
                "context": json.dumps(sanitize([best]), ensure_ascii=False),
                "hits": [best]
            }
            
        # 2) AMBIGUOUS
        # Rule D.1: If many matches but broad query -> List ALL (max reasonable)
        # Rule D.3: If user says "ทั้งหมด", list ALL.
        
        # Check "All" intent (passed via route?)
        limit = 10
        contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False)
        
        if route == "contact_ambiguous_all":
            limit = 50 # Max limit for "All"
            contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False)
        elif route == "contact_broad_list":
            limit = 50
            # Phase 235: Enable context for broad lists to allow selection (Fix "2" failure)
            contact_context = json.dumps(sanitize(candidates[:limit]), ensure_ascii=False)

        ans = format_candidate_list(candidates, max_items=limit)
        return {
            "answer": ans,
            "route": "contact_ambiguous" if route != "contact_broad_list" else route,
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
