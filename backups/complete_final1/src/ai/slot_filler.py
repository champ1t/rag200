"""
Slot Filler Module
Lightweight LLM for multi-turn clarify sessions.
Interprets user replies as answers to pending clarification questions.
"""
from typing import Dict, Any
import json
import time
from src.rag.ollama_client import ollama_generate


class SlotFiller:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.base_url = llm_cfg.get("base_url")
        self.model = llm_cfg.get("model")
        self.temperature = 0.0  # Deterministic
        
    def fill(self, user_input: str, pending_clarify: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill clarify session slots based on user input.
        
        Args:
            user_input: User's reply (e.g., "หลุดบ่อย")
            pending_clarify: Current clarify session state
            
        Returns:
        {
            "filled": {"slot_name": "value", ...},
            "still_needed": ["slot_name", ...],
            "next_question_th": "string",
            "all_filled": bool
        }
        """
        topic = pending_clarify.get("topic", "unknown")
        slots_needed = pending_clarify.get("slots_needed", [])
        slots_filled = pending_clarify.get("slots_filled", {})
        
        # Build slots status
        unfilled_slots = [s for s in slots_needed if not slots_filled.get(s)]
        
        prompt = f"""You are filling clarification slots. Interpret the user's reply and fill what you can.

Topic: {topic}
Slots needed: {', '.join(slots_needed)}
Currently filled: {json.dumps(slots_filled, ensure_ascii=False)}
Unfilled: {', '.join(unfilled_slots)}

User said: "{user_input}"

Task:
1. Interpret user input as answer to the most recent question
2. Fill any slots you can infer
3. Generate ONE short Thai question for the next most important missing slot
4. If all slots filled, set all_filled=true

Return JSON only:
{{
  "filled": {{"slot_name": "value"}},
  "still_needed": ["slot1", "slot2"],
  "next_question_th": "คำถามภาษาไทยสั้นๆ",
  "all_filled": false
}}"""

        try:
            resp = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=60,
                format="json"
            )
            
            result = json.loads(resp)
            
            # Validate
            if "filled" not in result:
                result["filled"] = {}
            if "still_needed" not in result:
                result["still_needed"] = unfilled_slots
            if "next_question_th" not in result:
                result["next_question_th"] = "กรุณาให้รายละเอียดเพิ่มเติมครับ"
            if "all_filled" not in result:
                result["all_filled"] = len(result["still_needed"]) == 0
                
            return result
            
        except Exception as e:
            print(f"[SlotFiller] Error: {e}")
            # Fallback
            return {
                "filled": {},
                "still_needed": unfilled_slots,
                "next_question_th": "กรุณาให้รายละเอียดเพิ่มเติมครับ",
                "all_filled": False
            }
