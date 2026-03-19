

from typing import Dict, Any
import time
import json
from src.rag.ollama_client import ollama_generate

PROMPT_SAFE_SHAPE_ANALYZER = """You are a highly sophisticated SAFE INTENT SHAPE ANALYZER for a deterministic enterprise directory system. Your primary role is to accurately interpret user queries, even those with colloquial Thai, informal phrasing, particles, and filler words, and map them to a structured JSON output.

GOAL
Decide whether the user wants:
(1) a SINGLE contact (one unit+location), or
(2) a LIST/TABLE of contacts (e.g., "มีอะไรบ้าง", "ทั้งหมด", "รายการ")

HARD RULES
- Do NOT output phone numbers, names, or links.
- Do NOT invent entities.
- Preserve known abbreviations exactly (e.g., OMC, RNOC, CSOC). Never split them into "O M C" or "OM C".
- If uncertain, choose CLARIFY and ask for the missing qualifier.
- Always prioritize the core intent and entities, filtering out conversational noise.

COLLOQUIAL THAI & NOISE HANDLING
- Ignore common Thai particles and polite markers like "ครับ", "ค่ะ", "นะ", "หน่อย", "ได้ไหม", "ได้มั้ย", "จ้า", "อ่ะ", "เอ่อ", "อืม".
- Focus on keywords and intent-bearing phrases, even if embedded in informal sentences.
- Recognize common informal synonyms or phrasing for official terms.

DETECTION RULES
- If query mentions "สมาชิก", "คนในทีม", "รายชื่อทีม", "ทีมงาน", "พวกพ้อง", "ใครอยู่ทีมนี้บ้าง" -> intent = "TEAM_LOOKUP", request_shape = "LIST"
- If query mentions "ใครคือ", "ใครเป็น", "ใครดูแล", "ใครดำรงตำแหน่ง", "ใครรับผิดชอบ", "คนไหน", "คนชื่ออะไร" (WHO IS) -> intent = "POSITION_LOOKUP", request_shape = "SINGLE"
- If query mentions "ตำแหน่ง [X]", "ตำแหน่งอะไร", "ตำแหน่งไหน" -> intent = "POSITION_LOOKUP"
- If query mentions "เบอร์", "เบอ", "ติดต่อ", "โทร", "พิกัด", "ที่ตั้ง", "อยู่ที่ไหน", "อยู่ตรงไหน", "ที่อยู่", "ช่องทางติดต่อ" -> intent = "CONTACT_LOOKUP" (EXCEPT "Fiber/ไฟเบอร์" -> NOT CONTACT)
- If query mentions "Check list", "Checklist", "วิธี", "ขั้นตอน", "คู่มือ", "ทำยังไง", "วิธีการ" -> intent = "HOWTO"
- If query mentions "มีอะไรบ้าง", "ทั้งหมด", "รายการ", "ทุกสาขา", "ลิสต์มาหน่อย", "ขอรายชื่อ" -> request_shape = "LIST"
- If query mentions "ข้อมูล", "รายละเอียด", "ความรู้", "อยากรู้เรื่อง", "หน้าที่", "รับผิดชอบ", "ทำอะไรบ้าง", "สโคปงาน" -> intent = "KNOWLEDGE"

OUTPUT (JSON ONLY)
{{
  "intent": "CONTACT_LOOKUP | TEAM_LOOKUP | POSITION_LOOKUP | ASSET | HOWTO | KNOWLEDGE | OTHER",
  "request_shape": "SINGLE | LIST | CLARIFY | ASSET",
  "canonical_query": "string",
  "entities": {{
    "unit": null | string,
    "location": null | string,
    "asset_type": null | "TABLE" | "IMAGE"
  }},
  "clarification_question": null | string,
  "confidence": 0.0-1.0
}}

STRICT RULE:
- NEVER transform a query about URLs or websites into technical hardware/config steps (like ONU/VLAN).
- If the user asks for "URL" or "Link", the intent MUST be "KNOWLEDGE" or "OTHER" (to trigger RAG), not "HOWTO".
- Preserve "SMC" as a unit. Do NOT expand "SMC" to other terms.

DETECTION RULES (ASSETS)
- If query contains "ตาราง", "ไฟล์ตาราง", "ลิสต์ตาราง", "ตารางข้อมูล", "ตารางเบอร์" -> request_shape = "ASSET", asset_type = "TABLE"
- If query contains "รูป", "ขอดูรูป", "แผนผัง", "ผัง", "ภาพ", "รูปภาพ" -> request_shape = "ASSET", asset_type = "IMAGE"

ENTITY EXTRACTION (CRITICAL)
- Extract the core "unit" (e.g., OMC, FTTx, HelpDesk, SMC, RNOC, CSOC).
- Remove noise words like "งาน", "ทีม", "ศูนย์", "ฝ่าย", "แผนก" from the "unit" entity.
- If it's a position like "ผจ.สบลตน.", the "unit" should be "สบลตน".
- Be flexible with casing for units (e.g., "omc" should be "OMC").

EXAMPLES
User: "ขอตารางเบอร์ OMC หน่อยครับ"
Output: {{"intent":"CONTACT_LOOKUP","request_shape":"ASSET","canonical_query":"ตารางเบอร์ OMC","entities":{{"unit":"OMC","location":null, "asset_type":"TABLE"}},"clarification_question":null,"confidence":1.0}}

User: "สมาชิก fttx มีใครบ้างอ่ะ"
Output: {{"intent":"TEAM_LOOKUP","request_shape":"LIST","canonical_query":"สมาชิก fttx","entities":{{"unit":"fttx","location":null}},"clarification_question":null,"confidence":1.0}}

User: "ใครคือ ผจ.สบลตน. ครับ"
Output: {{"intent":"POSITION_LOOKUP","request_shape":"SINGLE","canonical_query":"ใครคือ ผจ.สบลตน.","entities":{{"unit":"สบลตน","location":null}},"clarification_question":null,"confidence":1.0}}

User: "อยากรู้เบอร์ติดต่อของทีม HelpDesk จ้า"
Output: {{"intent":"CONTACT_LOOKUP","request_shape":"SINGLE","canonical_query":"เบอร์ติดต่อ HelpDesk","entities":{{"unit":"HelpDesk","location":null}},"clarification_question":null,"confidence":1.0}}

User: "มีขั้นตอนการทำงานของ CSOC ไหมครับ"
Output: {{"intent":"HOWTO","request_shape":"SINGLE","canonical_query":"ขั้นตอนการทำงาน CSOC","entities":{{"unit":"CSOC","location":null}},"clarification_question":null,"confidence":1.0}}

User: "ขอรายชื่อทั้งหมดของ NOC หน่อยนะ"
Output: {{"intent":"TEAM_LOOKUP","request_shape":"LIST","canonical_query":"รายชื่อทั้งหมด NOC","entities":{{"unit":"NOC","location":null}},"clarification_question":null,"confidence":1.0}}

ENTITY PRESERVATION RULES (STRICTEST)
- You MUST preserve EXACT tokens: OMC, RNOC, CSOC, NOC, FTTx, HelpDesk, SMC.
- NEVER add spaces inside acronyms (RNOC, not R N O C).

NOW PROCESS:
USER_QUERY: "{user_query}"
"""

PROMPT_QUERY_REWRITER = """Rewrite the Thai text to be CLEAN and STANDARD.
1. Remove polite particles (ครับ, ค่ะ, นะ, จ๊ะ, หน่อย, จ้า).
2. Remove conversational filler (ถามหน่อยดิ, อยากรู้ว่า, ขอลิงก์, ช่วยหา, มาให้หน่อย).
3. KEEP exact technical terms: OMC, RNOC, CSOC, NOC, FTTx, ONU, OLT, SMC, URL, Link.
4. DO NOT ADD NEW WORDS. DO NOT HALLUCINATE TECHNICAL TERMS.
5. If the user asks about "duty", "responsibility", or "what they do" (e.g., ทำหน้าที่อะไร, รับผิดชอบอะไร), DO NOT rewrite it to a person search. Keep the "duty" intent.
6. If the input is about "URL" or "Website", just keep the CORE subject.

Examples:
Input: ถามหน่อยดิ จะกำหนดค่า ONU ต้องทำยังไง
Output: กำหนดค่า ONU

Input: ขอรายชื่อ URL ของหน่วยงานที่เกี่ยวข้องทั้งหมดเลยครับ
Output: URL หน่วยงานที่เกี่ยวข้อง

Input: ช่วยหาเบอร์ติดต่อ SMC มาให้หน่อยดิ๊
Output: SMC

Input: {user_query}
Output:"""

class SafeNormalizer:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg
        self.model = llm_cfg.get("model", "llama3.2:3b")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")

    def _rewrite_query(self, query: str) -> str:
        """
        Stage 1: LLM rewrites colloquial/slangy Thai into clean standard Thai.
        Falls back to original query if LLM fails.
        """
        prompt = PROMPT_QUERY_REWRITER.format(user_query=query)
        try:
            t0 = time.time()
            res = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=0.0,
            )
            latency = (time.time() - t0) * 1000
            rewritten = res.strip().strip('"').strip("'").strip()
            # Safety: if rewritten is empty or too long (hallucination), use original
            if not rewritten or len(rewritten) > len(query) * 3:
                return query
            if rewritten != query:
                print(f"[QueryRewriter] '{query}' -> '{rewritten}' ({latency:.1f}ms)")
            return rewritten
        except Exception as e:
            print(f"[QueryRewriter] Fallback (error: {e})")
            return query

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        2-stage pipeline:
          Stage 1 — LLM rewrites colloquial/slang Thai to standard Thai
          Stage 2 — Intent classifier analyzes the clean query
        Returns a structured dictionary (JSON).
        """
        if len(query.strip()) < 2:
            return {"intent": "OTHER", "request_shape": "SINGLE", "canonical_query": query, "entities": {}, "confidence": 1.0}

        # Stage 1: Rewrite colloquial Thai
        clean_query = self._rewrite_query(query)

        # Stage 2: Intent classification on the clean query
        
        # --- HEURISTIC OVERRIDES (Phase 241) ---
        # Catch duty/responsibility before LLM hallucinations
        duty_keywords = ["หน้าที่", "รับผิดชอบ", "ทำอะไรบ้าง", "สโคปงาน", "ภารกิจ"]
        if any(k in query for k in duty_keywords):
            print(f"[SafeNormalizer] Heuristic HIT: KNOWLEDGE (duty)")
            return {
                "intent": "KNOWLEDGE",
                "request_shape": "SINGLE",
                "canonical_query": query,
                "entities": {"unit": None},
                "confidence": 1.0
            }
        
        # Catch Link/URL before LLM 
        link_keywords = ["ลิ้ง", "ลิงก์", "url", "เว็ป", "เว็บ", "link"]
        if any(k in query.lower() for k in link_keywords):
             print(f"[SafeNormalizer] Heuristic HIT: KNOWLEDGE (link)")
             return {
                "intent": "KNOWLEDGE",
                "request_shape": "SINGLE",
                "canonical_query": query,
                "entities": {"unit": None},
                "confidence": 1.0
            }
        
        prompt = PROMPT_SAFE_SHAPE_ANALYZER.format(user_query=clean_query)
        try:
            t0 = time.time()
            res = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=0.0,
                format="json"
            )
            latency = (time.time() - t0) * 1000
            data = json.loads(res)
            
            # Simple fallback if LLM hallucinates or returns invalid JSON (ollama_generate format="json" helps here)
            if not isinstance(data, dict) or "intent" not in data:
                return {"intent": "OTHER", "request_shape": "SINGLE", "canonical_query": query, "entities": {}, "confidence": 0.0}

            print(f"[SafeNormalizer] {query} -> {data.get('intent')} | {data.get('request_shape')} ({latency:.1f}ms)")
            return data
        except Exception as e:
            print(f"[SafeNormalizer] Error: {e}")
            return {"intent": "OTHER", "request_shape": "SINGLE", "canonical_query": query, "entities": {}, "confidence": 0.0}

    def normalize(self, query: str) -> str:
        """Legacy support for a single string return."""
        analysis = self.analyze(query)
        if analysis.get("confidence", 0) > 0.5:
            return analysis.get("canonical_query") or query
        return "NO_CHANGE"
