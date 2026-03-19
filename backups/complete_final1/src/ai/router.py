
import re
import logging
from typing import Dict, Any, List

class IntentRouter:
    """
    Hybrid Intent Router (Refactored V2).
    Classifies user queries into 6 strict intents to guide retrieval strategy.
    
    Taxonomy:
    1. CONTACT_LOOKUP: Asking for phone, email, contact channels.
    2. STATUS_CHECK: System status, availability, alarms.
    3. PERSON_LOOKUP: Asking for people, roles, members (without asking for contact info).
    4. HOWTO_PROCEDURE: Guides, settings, configs, problem solving.
    5. REFERENCE_LINK: Requesting URLs, forms, documents.
    6. GENERAL_QA: Everything else.
    """
    
    INTENTS = {
        "CONTACT_LOOKUP": [
            "เบอร์", "โทร", "ติดต่อ", "contact", "phone", "email", "mail", 
            "ext", "extension", "ช่องทาง", "สายด่วน", "hotline", "call",
            "เบอ", "เบอร", "โท"
        ],
        "STATUS_CHECK": [
            "สถานะ", "ใช้งานได้ไหม", "ล่ม", "alarm", "monitor", 
            "log", "incident", "status", "usage", "online", "offline",
            "ตรวจสอบ", "เช็ค", "check", "event", "system up", "link down" 
        ],
        "PERSON_LOOKUP": [
            "ใคร", "ผู้รับผิดชอบ", "สมาชิก", "ทีม", "บุคลากร", "เจ้าหน้าที่", 
            "คน", "staff", "member", "person", "who", "manager", "ผจก", "ผส.", 
            "ผอ.", "รายชื่อ", "หัวหน้า", "leader"
        ],
        "HOWTO_PROCEDURE": [
            "วิธี", "ขั้นตอน", "ตั้งค่า", "config", "คู่มือ", "แก้ไข", "ทำยังไง", 
            "แก้ปัญหา", "guide", "manual", "setup", "how to", "setting", 
            "procedure", "step", "แก้", "kb", "knowledge", "article", "doc", "แนวทาง"
        ],
        "REFERENCE_LINK": [
            "ขอลิงก์", "เอกสาร", "เว็บไซต์", "url", "download", "link", "website",
            "form", "แบบฟอร์ม", "หน้าเว็บ", "web"
        ],
        "MANAGEMENT_LOOKUP": [
            "ผู้บริหาร", "ผส.", "ผจ.", "ผู้อำนวยการ", "executives", "manager", "director", "management", 
            "หัวหน้าส่วน", "ผส.ป", "ผส.ต", "ผส.ก", "ผส.ย", "ผส.พ"
        ],
        "POSITION_HOLDER_LOOKUP": [
            "ใครตำแหน่ง", "ผู้ดำรงตำแหน่ง", "who is", "who holds", "ตำแหน่งใคร", "รักษาการ",
            "ใครเป็น", "ใครคือ", "ใครรับผิดชอบ"
        ],
        "NEWS_SEARCH": [
            "ข่าว", "ประกาศ", "news", "announcement", "ประชาสัมพันธ์", "update", "ล่าสุด", "นโยบาย", "new"
        ]
    }
    
    STRICT_ROUTER_PROMPT = """
You are a strict router for an internal RAG chatbot.
Your job: classify the user's query into one intent and extract minimal slots.
Rules:
- Be deterministic. Do NOT guess missing info.
- If ambiguous, return intent=CLARIFY with suggestions.
- Prefer precision over recall. Never hallucinate entities.
- CRITICAL: If query asks for Manual/Guide/PDF/SOP/Procedure (e.g. "manual", "คู่มือ", "วิธี"), return intent=HOWTO_PROCEDURE, even if a Team Name is present.
- Use Thai/English mixed queries.

### Strict Position Policy:
- If query is about a role/position (e.g. "ใครคือผจ", "ใครคือ ผส"), map to POSITION_HOLDER_LOOKUP.
- DO NOT use CLARIFY for short roles like "ผจ", "ผส". valid roles.
- Treat "ผจ", "ผส" as specific roles, not incomplete queries.

Return JSON only, strictly one line, no other text.
Format: {"intent": "ENUM_VALUE", "confidence": 0.9, "reason": "short explanation"}

Definitions:
- TEAM_LOOKUP: user asks members/personnel of a team/unit/งาน/ทีม/ฝ่าย (e.g., "บุคลากรงาน FTTx", "สมาชิก helpdesk", "ทีม Management SMC มีใครบ้าง")
- POSITION_HOLDER_LOOKUP: user asks who holds a role/position (e.g., "ใครตำแหน่ง ผส.บลตน", "ใครเป็น ชจญ.ภ.4")
- MANAGEMENT_LOOKUP: user asks executive list or top management (e.g., "รายชื่อผู้บริหาร", "ผู้บริหาร สบลตน")
- CONTACT_LOOKUP: user asks phone/email/contact info (e.g., "เบอร์งาน FTTx", "ขอเบอร์คุณสมบูรณ์", "อีเมล ผจ.สบลตน")
- HOWTO_PROCEDURE: how-to/config/fix steps (e.g., "แก้ user สำหรับลูกค้า context private", "ตั้งค่า TR069")
- WEB_KNOWLEDGE: External vendor specific (Cisco, Huawei), or News/Update questions (e.g. "ข่าว SMC ล่าสุด", "มาตรฐาน RFC 2684", "Cisco Bridge Port Config").
- INTERNAL_STANDARD: Specific internal standards (5S, ISO, KPI, Policy, Rule) -> Map to HOWTO_PROCEDURE.
- NEWS_SEARCH: (Deprecated -> Use WEB_KNOWLEDGE)
- REFERENCE_LINK: user asks for specific URLs, forms, or documents (e.g., "ขอลิงก์ edoc", "แบบฟอร์มใบลา")
- GENERAL_QA: chitchat, greetings, opinion questions, or off-topic queries (e.g., "สวัสดีครับ", "AIS ดีไหม", "รหัสผ่าน root")
- CLARIFY: incomplete query like "ใครตำแหน่ง" or "เบอร์ผส"

Normalization:
- Strip polite particles: "ครับ", "ค่ะ", "หน่อย", "หน่อยนะ", "ที", "ทีครับ"
- Normalize spacing and punctuation (e.g., "ผจ สบลตน" -> "ผจ.สบลตน")
- Treat "บุคลากร", "สมาชิก", "รายชื่อ", "ทีม", "งาน" as TEAM signals unless explicitly asking executive.
- Treat "ใคร", "คร", "ตำแหน่ง", "เป็นใคร" as ROLE holder signals.
- Treat "เบอร์", "โทร", "ติดต่อ", "อีเมล" as CONTACT signals.
- If query contains both TEAM and CONTACT signals, set intent=CONTACT_LOOKUP and need=phone but keep team slot.




- CRITICAL: Treat "ผจ", "ผส", "ผอ" as specific MANAGEMENT_LOOKUP strategies. Do NOT classify as CLARIFY.

Now classify this user query:
<<<USER_QUERY>>>
    """

    def __init__(self, llm_config: Dict[str, Any] = None):
        self.llm_config = llm_config
        
    def route(self, query: str) -> Dict[str, Any]:
        """
        Route the query to an intent.
        Tries Strict LLM Routing first. Fallbacks to Keyword V2 if fail.
        """
        query_lower = query.lower().strip()
        
        # Phase 135: Strict Location + Contact Heuristic (Pre-LLM Fast Path)
        # "เบอร์ ... ตรัง", "เบอร์ ... หาดใหญ่", "เบอร์ ... ภูเก็ต"
        # If explicit "Phone" keyword appears with known locations or "สื่อสารข้อมูล" (Dept), force CONTACT.
        force_contact_triggers = ["สื่อสารข้อมูล", "omc", "service", "customer"]
        locations = ["ตรัง", "ภูเก็ต", "หาดใหญ่", "สงขลา", "สตูล", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส", "นครศรี", "สุราษ", "ชุมพร", "ระนอง", "กระบี่", "พังงา"]
        
        has_phone = any(k in query_lower for k in ["เบอร์", "โทร", "call", "hotline", "สายด่วน"])
        has_force_trigger = any(t in query_lower for t in force_contact_triggers)
        has_location = any(l in query_lower for l in locations)
        
        if has_phone and (has_force_trigger or has_location):
             return {"intent": "CONTACT_LOOKUP", "confidence": 1.0, "reason": "Strict Phone+Location/Dept Match"}
        
        # 1. Try LLM Routing (Strict)
        if self.llm_config:
            try:
                return self._route_llm(query)
            except Exception as e:
                # Log warning but fallback strictly
                print(f"[Router] LLM Routing Failed: {e}. Falling back to Keyword Router.")
        
        # 2. Fallback to Regex/Hybrid (V2 Logic)
        return self._route_regex(query)

    def _route_llm(self, query: str) -> Dict[str, Any]:
        from src.rag.ollama_client import ollama_generate
        import json
        # import re
        
        prompt = self.STRICT_ROUTER_PROMPT.replace("<<<USER_QUERY>>>", query)
        
        # Deterministic params
        resp = ollama_generate(
            base_url=self.llm_config.get("base_url", "http://localhost:11434"),
            model=self.llm_config.get("fast_model", "llama3.2:3b"), # Phase 135: Use Fast Model
            prompt=prompt,
            temperature=0.0,
            num_predict=256, # Phase 127: Fast Routing
            num_ctx=2048     # Phase 127: Short Context
        )
        
        # 1. Regex Extraction (Find first {...})
        match = re.search(r"\{.*?\}", resp, re.DOTALL)
        if match:
            clean_resp = match.group(0)
        else:
            # Maybe it wrapped it in code blocks without braces? Unlikely but possible.
            # Strip code blocks just in case
            clean_resp = resp.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(clean_resp)
        except json.JSONDecodeError as e:
            # Fallback for malformed JSON (e.g. usage of single quotes, missing keys)
            # Try fixing single quotes
            try:
                fixed = clean_resp.replace("'", '"')
                data = json.loads(fixed)
            except:
                raise ValueError(f"CRITICAL: Failed to parse Router JSON: {clean_resp[:50]}...") from e

        # 2. Validate Keys & Enum
        allowed_intents = set(self.INTENTS.keys()).union({"CLARIFY", "GENERAL_QA", "TEAM_LOOKUP", "WEB_KNOWLEDGE"})
        intent = data.get("intent", "GENERAL_QA")
        
        if intent not in allowed_intents:
             # Fallback to GENERAL_QA if intent is hallucinated
             print(f"[Router] Warn: LLM hallucinated intent '{intent}'. Mapping to GENERAL_QA.")
             intent = "GENERAL_QA"
             
        res = {
            "intent": intent,
            "confidence": float(data.get("confidence", 0.0)),
            "reason": data.get("reason", "LLM Decision"), # Standardize key
            "slots": { # Extra slots for future use
                "team": data.get("team"),
                "role": data.get("role"),
                "person": data.get("person"),
                "topic": data.get("topic"),
                "need": data.get("need")
            },
            "suggestions": data.get("suggestions", [])
        }
        return res

    def _route_regex(self, query: str) -> Dict[str, Any]:
        """
        Original Hybrid Intent Router (Refactored V2).
        Classifies user queries into 6 strict intents to guide retrieval strategy.
        """
        query_lower = query.lower().strip()
        
        # Phase 135: Strict Location + Contact Heuristic
        # "เบอร์ ... ตรัง", "เบอร์ ... หาดใหญ่", "เบอร์ ... ภูเก็ต"
        # If explicit "Phone" keyword appears with known locations or "สื่อสารข้อมูล" (Dept), force CONTACT.
        force_contact_triggers = ["สื่อสารข้อมูล", "omc", "service", "customer"]
        locations = ["ตรัง", "ภูเก็ต", "หาดใหญ่", "สงขลา", "สตูล", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส", "นครศรี", "สุราษ", "ชุมพร", "ระนอง", "กระบี่", "พังงา"]
        
        has_phone = any(k in query_lower for k in ["เบอร์", "โทร", "call", "hotline", "สายด่วน"])
        has_force_trigger = any(t in query_lower for t in force_contact_triggers)
        has_location = any(l in query_lower for l in locations)
        
        if has_phone and (has_force_trigger or has_location):
             return {"intent": "CONTACT_LOOKUP", "confidence": 1.0, "reason": "Strict Phone+Location/Dept Match"}
        
        # Priority 1: CONTACT_LOOKUP
        # Rule: Any distinct contact keyword triggers this.
        # User Constraint: "CONTACT_LOOKUP must win over PERSON_LOOKUP"
        
        # Refined Logic (Phase 44): Filter out false positives (e.g. "context" -> "ext")
        contact_hits = [k for k in self.INTENTS["CONTACT_LOOKUP"] if k in query_lower]
        valid_contact_hits = []
        for h in contact_hits:
            # "ext" safety: ignore if part of "context", "text", "next", "external"
            if h == "ext":
                 if "context" in query_lower or "text" in query_lower or "next" in query_lower:
                    continue
            valid_contact_hits.append(h)

        if valid_contact_hits:
             # Procedural Override (Negative Rule)
             procedural_terms = ["วิธี", "howto", "ขั้นตอน", "แก้", "fix", "config", "setting", "setup", "คู่มือ", "เปลี่ยน", "change"]
             is_procedure = any(t in query_lower for t in procedural_terms)
             
             strong_contact = any(t in query_lower for t in ["เบอร์", "โทร", "call", "hotline", "สายด่วน"])
             
             if is_procedure and not strong_contact:
                  return {"intent": "HOWTO_PROCEDURE", "confidence": 0.85, "reason": "Procedural Keyword Dominates Weak Contact"}

             return {"intent": "CONTACT_LOOKUP", "confidence": 0.95, "reason": "Contact Keyword Match"}

        # Priority 1.2: TEAM_LOOKUP (Specific Team Members) - Phase 69
        # Check for explicit team keywords ("งาน", "ทีม", "กลุ่ม") - Moved UP to beat Position Holder
        team_indicators = ["งาน", "ทีม", "กลุ่ม", "ฝ่าย", "ส่วน", "กอง"]
        if any(ti in query_lower for ti in team_indicators):
             if any(re.search(fr"{ti}\s*[A-Za-z0-9ก-๙]+", query_lower) for ti in team_indicators):
                  return {"intent": "TEAM_LOOKUP", "confidence": 0.9, "reason": "Team Keyword 'งาน/ทีม' Match"}

        # Priority 1.3: POSITION_HOLDER_LOOKUP (Specific "Who is X")
        # Only if not a clear Team Lookup
        pos_holder_patterns = [
            r"(?:ใคร|คร)\s*ตำแหน่ง", r"ตำแหน่ง\s*.*\s*(?:ใคร|คร)", r"(?:ใคร|คร)\s*.*\s*ตำแหน่ง", 
            r"ผู้ดำรงตำแหน่ง", r"(?:ใคร|คร)\s*รับผิดชอบ", r"(?:ใคร|คร)\s*คือ", r"(?:ใคร|คร)\s*เป็น",
            r"who\s*is", r"who\s*holds"
        ]
        # import re  <-- Removed redundant import preventing scope issues
        if any(re.search(p, query_lower) for p in pos_holder_patterns):
             return {"intent": "POSITION_HOLDER_LOOKUP", "confidence": 0.95, "reason": "Position Holder Regex Match"}
             
        # Keyword Fallback (just in case)
        if any(k in query_lower for k in self.INTENTS["POSITION_HOLDER_LOOKUP"]):
             return {"intent": "POSITION_HOLDER_LOOKUP", "confidence": 0.95, "reason": "Position Holder Keyword Match"}

        # Priority 1.5: MANAGEMENT_LOOKUP (Specific Executive/Role Lookup)
        if any(k in query_lower for k in self.INTENTS["MANAGEMENT_LOOKUP"]):
             return {"intent": "MANAGEMENT_LOOKUP", "confidence": 0.95, "reason": "Management Keyword Match"}

        
        # Priority 2: STATUS_CHECK
        if any(k in query_lower for k in self.INTENTS["STATUS_CHECK"]):
             return {"intent": "STATUS_CHECK", "confidence": 0.9, "reason": "Status Keyword Match"}

        # Priority 2.5: DOCUMENT/MANUAL GATING (Phase 72)
        # Prevent "FTTx Manual" from falling into Person/Team Lookup
        doc_triggers = ["คู่มือ", "manual", "วิธี", "ขั้นตอน", "เอกสาร", "pdf", "ดาวน์โหลด", "guide", "how to", "config", "setup", "sop", "procedure"]
        is_document = any(t in query_lower for t in doc_triggers)
        
        # If document intent is strong, route to HOWTO immediately UNLESS it asks for "Who" explicitly
        if is_document:
            return {"intent": "HOWTO_PROCEDURE", "confidence": 0.9, "reason": "Document/Manual Keyword Match"}

        # Priority 3: INTERNAL STANDARD (5S, ISO) -> HOWTO
        standard_triggers = ["5ส", "5s", "iso", "kpi", "มาตรฐาน"]
        if any(t in query_lower for t in standard_triggers):
             # Distinguish External Standard (RFC) vs Internal
             if "rfc" not in query_lower and "ieee" not in query_lower:
                 return {"intent": "THAI_ORG_KNOWLEDGE", "confidence": 0.95, "reason": "Internal Standard (5S/ISO) Match - Force Thai Rule"}



        # Priority 3.5: PERSON_LOOKUP (General "Who")
        if any(k in query_lower for k in self.INTENTS["PERSON_LOOKUP"]):
             if "โอน" in query_lower:
                 return {"intent": "HOWTO_PROCEDURE", "confidence": 0.8, "reason": "Keyword 'Transfer' -> HowTo"}
             
             # Phase 72: Distinguish Team vs Person?
             # If "สมาชิก", "บุคลากร", "ทีม" -> Use TEAM_LOOKUP intent tag if possible?
             # ChatEngine supports TEAM_LOOKUP.
             team_kws = ["สมาชิก", "ทีม", "บุคลากร", "รายชื่อ"]
             if any(tk in query_lower for tk in team_kws):
                 return {"intent": "TEAM_LOOKUP", "confidence": 0.9, "reason": "Team Keyword Match"}
             
             return {"intent": "PERSON_LOOKUP", "confidence": 0.85, "reason": "Person Keyword Match"}
             
        # Priority 4: REFERENCE_LINK
        if any(k in query_lower for k in self.INTENTS["REFERENCE_LINK"]):
             return {"intent": "REFERENCE_LINK", "confidence": 0.9, "reason": "Link Keyword Match"}
             
        # Priority 4.5: NEWS_SEARCH
        if any(k in query_lower for k in self.INTENTS["NEWS_SEARCH"]):
             return {"intent": "NEWS_SEARCH", "confidence": 0.85, "reason": "News Keyword Match"}
             
        # Priority 5: HOWTO_PROCEDURE (Broader match)
        if any(k in query_lower for k in self.INTENTS["HOWTO_PROCEDURE"]):
             return {"intent": "HOWTO_PROCEDURE", "confidence": 0.85, "reason": "HowTo Keyword Match"}
             
        # Regex Fallbacks
        if re.search(r"(ทำ|แก้|ใช้|โอน).*?(อย่างไร|ยังไง|ไหม|สาย)", query_lower):
            return {"intent": "HOWTO_PROCEDURE", "confidence": 0.7, "reason": "Regex Pattern"}

        # Priority 6: GENERAL_QA
        return {"intent": "GENERAL_QA", "confidence": 1.0, "reason": "Default Fallback"}
