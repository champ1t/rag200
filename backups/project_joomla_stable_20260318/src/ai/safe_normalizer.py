

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
- If query mentions "ข้อมูล", "รายละเอียด", "ความรู้", "อยากรู้เรื่อง" -> intent = "KNOWLEDGE"

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

PROMPT_QUERY_REWRITER = """Rewrite the Thai text below. Remove filler words, slang, and polite particles. Keep technical terms and entity names exactly. Output ONLY the rewritten Thai text, nothing else.

Filler words to remove: ถามหน่อย, ถามหน่อยดิ, อยากถาม, ขอถามว่า, ช่วยบอก, บอกหน่อย, หน่อย, ดิ, ดิ๊, วะ, อ่ะ, หว่า, สิ, เฮ้ย, หรอฮัฟ, ครับ, ค่ะ, นะ, จ้า, นะจ๊ะ, นะครับ, นะคะ, หน่อยนะ, มาให้หน่อย, ช่วยหา, ขอเบอร์, อยู่ไหน, ตรงไหน, ทราบไหม, ใครคือ, ชื่ออะไร, มาให้
Keep exactly: OMC, RNOC, CSOC, NOC, FTTx, ONU, OLT, ZTE, Huawei, BRAS, VLAN, ADSL, FTTX, IP, ผจ, ผจก, ผอ, ช.สาย

Abbreviation expansions: ผจ/ผจก→ผู้จัดการ, ผอ→ผู้อำนวยการ, ช.สาย→ช่างสาย

Examples:
Thai: ถามหน่อยดิ จะกำหนดค่า ONU ต้องทำยังไง
Clean: วิธีกำหนดค่า ONU

Thai: ขอถามว่า ใครคือผจ หรอฮัฟ
Clean: ผจ

Thai: ช่วยหาเบอร์ศูนย์ชุมพรมาให้หน่อย
Clean: ศูนย์ชุมพร

Thai: ขอเบอร์ติดต่อ SMC หน่อยดิ๊
Clean: SMC

Thai: {user_query}
Clean:"""

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
