
import re
from typing import Dict, Any, Optional, List
from src.utils.extractors import extract_location_intent, is_valid_mapping_line, SCAN_KEYS, ABBREVIATIONS, strip_footer_noise

class DispatchMapper:
    """
    Specialized handler for 'Dispatch/SCOMS/Circuit Rental' queries.
    Refactored to use shared `src.utils.extractors`.
    """
    
    # Trigger keywords
    TRIGGERS = ["จ่ายงาน", "วงจรเช่า", "scoms", "เลขหมาย"]
    
    # Target Article Title Keywords (to find correct doc in cache)
    ARTICLE_TITLE_KWS = ["การจ่ายงานเลขหมายวงจรเช่า"]
    
    @classmethod
    def is_match(cls, query: str) -> bool:
        q_lower = query.lower()
        has_jayan = "จ่ายงาน" in q_lower
        has_context = any(k in q_lower for k in ["วงจร", "scoms", "เลขหมาย"])
        return has_jayan and has_context

    @classmethod
    def handle(cls, query: str, processed_cache: Any) -> Dict[str, Any]:
        """
        Handles the query by looking up specific province info in the Dispatch Article.
        """
        # 1. Find the article
        target_doc = None
        for url, text in processed_cache._url_to_text.items():
            if all(k in text for k in cls.ARTICLE_TITLE_KWS):
                target_doc = text
                break
        
        if not target_doc:
             return {
                 "answer": "ไม่พบข้อมูลระเบียบการจ่ายงานในระบบ (Article Not Found)",
                 "route": "dispatch_mapper_error"
             }

        # 2. Extract Intents
        req_locations = extract_location_intent(query)
        q_lower = query.lower()
        
        # Sub-Intents (Item 2: SMS, Item 3: Central)
        intent_sms = any(k in q_lower for k in ["sms", "ข้อ 2", "ข้อ2", "ขั้นตอนส่ง", "วิธีส่ง"])
        intent_central = any(k in q_lower for k in ["ส่วนกลาง", "ข้อ 3", "ข้อ3", "สาเหตุ"])

        # 3. Parse Article into Map
        # NEW: Pre-strip noise
        clean_doc = strip_footer_noise(target_doc)
        province_map = cls._parse_dispatch_article(clean_doc)
        
        # 4. Formulate Answer
        answers = []
        
        # Priority: Specific Item Request
        if intent_sms:
            content = province_map.get("SECTION_2", "ไม่พบข้อมูลขั้นตอนส่ง SMS (ข้อ 2)")
            answers.append(f"**ข้อ 2: แนวทางส่ง SMS**\n{content}")
        
        if intent_central:
            content = province_map.get("SECTION_3", "ไม่พบข้อมูลกรณีสาเหตุส่วนกลาง (ข้อ 3)")
            answers.append(f"**ข้อ 3: กรณีสาเหตุอยู่ส่วนกลาง**\n{content}")
            
        # If no specific item requested, OR explicit location requested
        if req_locations and not (intent_sms or intent_central):
            missing = []
            valid_locs = False
            for loc in req_locations:
                if loc in province_map:
                    content = province_map[loc]
                    
                    # NEW: Line Deduplication
                    lines = content.split('\n')
                    uniq_lines = []
                    seen = set()
                    for ln in lines:
                        ln_s = ln.strip()
                        if not ln_s: continue
                        if ln_s not in seen:
                            seen.add(ln_s)
                            uniq_lines.append(ln)
                    
                    content = "\n".join(uniq_lines)

                    # Robustness: Check for "Sparse" content
                    import re
                    has_digits = bool(re.search(r"\d", content))
                    if len(content) < 50 and not has_digits:
                        content += "\n(ไม่พบรหัส/เลขหมายเพิ่มเติมในบทความนี้)"
                    
                    answers.append(f"**{loc}**\n{content}")
                    valid_locs = True
                else:
                    # Fallback Regex Search (Robustness B)
                    import re
                    # Look for Loc roughly at start of line (handling Markdown ** or ##)
                    # matches: "\nตรัง", "\n**ตรัง", "\n## ตรัง"
                    fallback_match = re.search(r"(?:^|\n)\s*(?:[\*\#]+\s*)?" + re.escape(loc), clean_doc)
                    if fallback_match:
                         start_idx = fallback_match.start()
                         # Take next 500 chars limit
                         chunk = clean_doc[start_idx:start_idx+500]
                         chunk_lines = chunk.split('\n')
                         valid_chunk = []
                         found_header = False
                         for cl in chunk_lines:
                             if loc in cl: 
                                 found_header = True
                                 valid_chunk.append(f"**{cl.strip()}**")
                                 continue
                             if not found_header: continue
                             
                             if is_valid_mapping_line(cl) or len(cl.strip()) < 50:
                                 if len(cl.strip()) > 3 and not any(char.isdigit() for char in cl) and " " not in cl.strip():
                                     break
                                 valid_chunk.append(cl.strip())
                         
                         if len(valid_chunk) > 1:
                             content = "\n".join(valid_chunk)
                             answers.append(f"**{loc} (Fallback)**\n{content}")
                             valid_locs = True
                             continue

                    missing.append(loc)
            
            if missing and not valid_locs:
                 # If found NOTHING, return empty answers to trigger Helper
                 answers = []
        
        # Helper Message (Phase 36)
        if not answers:
             # Provide valid keys to help user
             keys = sorted([k for k in province_map.keys() if "SECTION" not in k])[:20] # Limit
             sample = ", ".join(keys)
             msg = f"ไม่พบข้อมูลพื้นที่ที่ระบุ ในระบบมีข้อมูลของ: {sample}..."
             if intent_sms: msg = "ไม่พบข้อมูลขั้นตอน SMS"
             
             return {
                 "answer": msg,
                 "route": "dispatch_mapper_general", # Signal to ChatEngine to ask only for province
                 "context": "awaiting_province" # Logic C
             }

        final_ans = "\n\n".join(answers)
        return {
            "answer": final_ans,
            "route": "dispatch_mapper_hit"
        }

    @classmethod
    def handle_followup(cls, query: str, processed_cache: Any) -> Dict[str, Any]:
        """
        Force-handle a query as a Province/Location (Logic C).
        Wrapper around handle() but skips is_match check.
        """
        # Synthesize a query that extraction will understand?
        # Or just rely on extract_location_intent finding valid province in `query`.
        # If query is "ปัตตนี", fuzzy match in extract_location_intent should work.
        
        # We assume the query IS the location.
        # But we need to call `handle` to reuse logic.
        # BUT `handle` requires `query` to pass `extract_location_intent`.
        return cls.handle(query, processed_cache)

    @staticmethod
    def _parse_dispatch_article(text: str) -> Dict[str, str]:
        """
        Parses text into Provinces and Sections (Policy).
        """
        lines = text.split('\n')
        data_map = {}
        current_key = None
        buffer = []
        is_policy_mode = False
        
        STOP_KEYWORDS = ["joomla", "template", "แก้ไขล่าสุด", "คู่มือ", "login", "forgot password", "reset"]
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean: continue
            line_lower = line_clean.lower()
            
            # 1. Global Stop (Backup)
            # Handled upstream mostly, but good for safety
            
            # 2. Check Province Header
            matched_prov = None
            if len(line_clean) < 40:
                for key in SCAN_KEYS:
                    if key in line_lower:
                         matched_prov = ABBREVIATIONS.get(key, key)
                         break
            
            # Priority: Province Header overrides Section? 
            # Usually Sections are big blocks. Provinces are lists.
            # If we find a province header, we switch to Province Mode.
            
            if matched_prov:
                # Is Province Header
                if current_key and buffer:
                    # Flush Previous
                    existing = data_map.get(current_key, "")
                    new_block = "\n".join(buffer).strip()
                    if existing and new_block:
                        data_map[current_key] = existing + "\n\n" + new_block
                    elif new_block:
                        data_map[current_key] = new_block
                
                current_key = matched_prov
                buffer = []
                is_policy_mode = False
                
                # Check inline content
                if is_valid_mapping_line(line_clean):
                     buffer.append(line_clean)

            else:
                # Not a province header.
                # Check for "Policy Section" break (numbered list start: "1.", "2.")
                # We capture them as "SECTION_1", "SECTION_2"
                m = re.match(r"^(\d+)\.", line_clean)
                if m:
                    # Switch to Section Mode
                    if current_key and buffer:
                        existing = data_map.get(current_key, "")
                        new_block = "\n".join(buffer).strip()
                        if existing and new_block:
                             data_map[current_key] = existing + "\n\n" + new_block
                        elif new_block:
                             data_map[current_key] = new_block
                    
                    section_num = m.group(1)
                    current_key = f"SECTION_{section_num}"
                    buffer = [line_clean] # Start with header
                    is_policy_mode = True
                    continue
                
                # 3. Content Line Confirmation
                if current_key:
                    if is_policy_mode:
                        # Capture ALL content in Policy Mode (relaxed)
                        # Maybe exclude obvious footer noise if not stripped?
                        buffer.append(line_clean)
                    else:
                        # Province Mode: Strict
                        if is_valid_mapping_line(line_clean):
                            buffer.append(line_clean)
        
        # Final Flush
        if current_key and buffer:
            existing = data_map.get(current_key, "")
            new_block = "\n".join(buffer).strip()
            if existing and new_block:
                 data_map[current_key] = existing + "\n\n" + new_block
            elif new_block:
                 data_map[current_key] = new_block
            
        return data_map

