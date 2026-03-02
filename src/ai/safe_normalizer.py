
from typing import Dict, Any
import time
import json
from src.rag.ollama_client import ollama_generate

PROMPT_SAFE_SHAPE_ANALYZER = """You are a SAFE INTENT SHAPE ANALYZER for a deterministic enterprise directory system.

GOAL
Decide whether the user wants:
(1) a SINGLE contact (one unit+location), or
(2) a LIST/TABLE of contacts (e.g., "มีอะไรบ้าง", "ทั้งหมด", "รายการ")

HARD RULES
- Do NOT output phone numbers, names, or links.
- Do NOT invent entities.
- Preserve known abbreviations exactly (e.g., OMC, RNOC, CSOC). Never split them into "O M C" or "OM C".
- If uncertain, choose CLARIFY and ask for the missing qualifier.

DETECTION RULES
- If query mentions "สมาชิก", "คนในทีม", "รายชื่อทีม" -> intent = "TEAM_LOOKUP", request_shape = "LIST"
- If query mentions "ใครคือ", "ใครเป็น", "ใครดูแล", "ใครดำรงตำแหน่ง" (WHO IS) -> intent = "POSITION_LOOKUP", request_shape = "SINGLE"
- If query mentions "ตำแหน่ง [X]" -> intent = "POSITION_LOOKUP"
- If query mentions "เบอร์", "เบอ", "ติดต่อ", "โทร", "พิกัด", "ที่ตั้ง", "อยู่ที่ไหน", "อยู่ตรงไหน", "ที่อยู่" -> intent = "CONTACT_LOOKUP" (EXCEPT "Fiber/ไฟเบอร์" -> NOT CONTACT)
- If query mentions "Check list", "Checklist", "วิธี", "ขั้นตอน", "คู่มือ" -> intent = "HOWTO"
- If query mentions "มีอะไรบ้าง", "ทั้งหมด", "รายการ", "ทุกสาขา" -> request_shape = "LIST"

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
- If query contains "ตาราง", "ไฟล์ตาราง", "ลิสต์ตาราง" -> request_shape = "ASSET", asset_type = "TABLE"
- If query contains "รูป", "ขอดูรูป", "แผนผัง", "ผัง" -> request_shape = "ASSET", asset_type = "IMAGE"

ENTITY EXTRACTION (CRITICAL)
- Extract the core "unit" (e.g., OMC, FTTx, HelpDesk, SMC, RNOC, CSOC).
- Remove noise words like "งาน", "ทีม", "ศูนย์" from the "unit" entity.
- If it's a position like "ผจ.สบลตน.", the "unit" should be "สบลตน".

EXAMPLES
User: "ขอตารางเบอร์ OMC"
Output: {{"intent":"CONTACT_LOOKUP","request_shape":"ASSET","canonical_query":"ตารางเบอร์ OMC","entities":{{"unit":"OMC","location":null, "asset_type":"TABLE"}},"clarification_question":null,"confidence":1.0}}

User: "สมาชิก fttx"
Output: {{"intent":"TEAM_LOOKUP","request_shape":"LIST","canonical_query":"สมาชิก fttx","entities":{{"unit":"fttx","location":null}},"clarification_question":null,"confidence":1.0}}

User: "ใครคือ ผจ.สบลตน."
Output: {{"intent":"POSITION_LOOKUP","request_shape":"SINGLE","canonical_query":"ใครคือ ผจ.สบลตน.","entities":{{"unit":"สบลตน","location":null}},"clarification_question":null,"confidence":1.0}}

ENTITY PRESERVATION RULES (STRICTEST)
- You MUST preserve EXACT tokens: OMC, RNOC, CSOC, NOC, FTTx, HelpDesk, SMC.
- NEVER add spaces inside acronyms (RNOC, not R N O C).

NOW PROCESS:
USER_QUERY: "{user_query}"
"""

class SafeNormalizer:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg
        self.model = llm_cfg.get("model", "llama3.2:3b")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyzes the query for intent, shape, and entities.
        Returns a structured dictionary (JSON).
        """
        if len(query.strip()) < 2:
            return {"intent": "OTHER", "request_shape": "SINGLE", "canonical_query": query, "entities": {}, "confidence": 1.0}

        prompt = PROMPT_SAFE_SHAPE_ANALYZER.format(user_query=query)
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
