"""
AI Planner Module
Lightweight LLM-based query planner that detects:
- Strategy (USE_LAST_CONTEXT, DO_LOOKUP, RAG, CLARIFY, NO_ANSWER)
- Entity (role/person/dept)
- Output Mode (PHONE_ONLY, EMAIL_ONLY, FAX_ONLY, LINK_ONLY, FULL_CARD)
"""
from typing import Dict, Any, Optional
import json
import time
from src.rag.ollama_client import ollama_generate


class QueryPlanner:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.base_url = llm_cfg.get("base_url")
        self.model = llm_cfg.get("model")
        self.temperature = 0.0  # Deterministic
        
    def plan(self, query: str, last_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze query and return execution plan.
        
        Returns:
        {
            "strategy": "USE_LAST_CONTEXT"|"DO_LOOKUP"|"RAG"|"CLARIFY"|"NO_ANSWER",
            "entity": {"text": str|null, "type": "ROLE"|"PERSON"|"DEPT"|null},
            "output_mode": "FULL_CARD"|"PHONE_ONLY"|"EMAIL_ONLY"|"FAX_ONLY"|"LINK_ONLY"|"SOURCE_ONLY",
            "confidence": 0.0-1.0
        }
        """
        # Build context summary
        ctx_summary = "None"
        if last_context:
            ctx_type = last_context.get("type", "unknown")
            ctx_ref = last_context.get("ref_name", "unknown")
            ctx_summary = f"{ctx_type}:{ctx_ref}"
        
        prompt = f"""You are a query planner. Analyze the user query and return a JSON plan.

DETECTION RULES:
1. Output Mode (detect "only" intent):
   - "ขอแค่เบอร์/เบอร์อย่างเดียว/เอาแค่เบอร์/only phone" → PHONE_ONLY
   - "ขอแค่เมล/อีเมลอย่างเดียว/only email" → EMAIL_ONLY
   - "ขอแค่แฟกซ์/โทรสารอย่างเดียว/only fax" → FAX_ONLY
   - "ขอแค่ลิงก์/URL อย่างเดียว/only link" → LINK_ONLY
   - "ขอแค่ชื่อ/only name" → NAME_ONLY
   - Default → FULL_CARD

2. Strategy:
   - If query has entity (role/person/dept) → DO_LOOKUP
   - If query lacks entity but last_context exists → USE_LAST_CONTEXT
   - If query lacks entity and no context → CLARIFY
   - If query is greeting/thanks → NO_ANSWER

3. Entity:
   - Extract role/person/dept name if present
   - Type: ROLE (ผจ, ผส, etc.) | PERSON (name) | DEPT (department)

User Query: "{query}"
Last Context: {ctx_summary}

Return JSON only (no explanation):
{{
  "strategy": "...",
  "entity": {{"text": "...", "type": "..."}},
  "output_mode": "...",
  "confidence": 0.0-1.0
}}"""

        try:
            resp = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=80,
                format="json"
            )
            
            plan = json.loads(resp)
            
            # Validate and set defaults
            if "strategy" not in plan:
                plan["strategy"] = "RAG"
            if "output_mode" not in plan:
                plan["output_mode"] = "FULL_CARD"
            if "entity" not in plan:
                plan["entity"] = {"text": None, "type": None}
            if "confidence" not in plan:
                plan["confidence"] = 0.5
                
            return plan
            
        except Exception as e:
            print(f"[QueryPlanner] Error: {e}")
            # Fallback plan
            return {
                "strategy": "RAG",
                "entity": {"text": None, "type": None},
                "output_mode": "FULL_CARD",
                "confidence": 0.0
            }
