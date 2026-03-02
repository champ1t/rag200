
from typing import Dict, Any, Optional
import random

class GreetingsHandler:
    """
    Handles deterministic greetings and chitchat responses, bypassing the LLM.
    Strictly follows User Rule: No Cache for Greetings.
    """
    
    GREETING_PATTERNS = {"สวัสดี", "ทักทาย", "hello", "hi", "hey", "ฮัลโหล", "หวัดดี"}
    THANKS_PATTERNS = {"ขอบคุณ", "ขอบใจ", "thanks", "thank", "thx"}
    ACK_PATTERNS = {"รับทราบ", "โอเค", "ok", "ครับ", "ค่ะ", "เข้าใจแล้ว"}
    
    # Deterministic Templates
    GREETING_TEMPLATE = "สวัสดีครับ ต้องการให้ช่วยเรื่องอะไรครับ (เช่น เบอร์หน่วยงาน, รายชื่อทีม, หรือความรู้ SMC)"
    THANKS_TEMPLATE = "ยินดีให้บริการครับ หากมีข้อสงสัยเพิ่มเติมสอบถามได้เสมอครับ"
    ACK_TEMPLATE = "รับทราบครับ"

    def handle(self, query: str, intent: str) -> Optional[Dict[str, Any]]:
        """
        Checks if the query is a greeting/short chitchat and returns a deterministic response.
        Returns None if not a greeting.
        """
        query_norm = query.lower().strip()
        
        # Check by Intent (Strongest Signal)
        if intent == "GENERAL_QA" and len(query_norm) < 15: # Short General QA only
             if any(p in query_norm for p in self.GREETING_PATTERNS):
                 return self._response(self.GREETING_TEMPLATE)
             if any(p in query_norm for p in self.THANKS_PATTERNS):
                 return self._response(self.THANKS_TEMPLATE)
             if any(p in query_norm for p in self.ACK_PATTERNS):
                 return self._response(self.ACK_TEMPLATE)
        
        # Specifically for "GREETING", "THANKS", "ACK" intents if we had them in Router
        # Since Router maps most to GENERAL_QA, the keyword check above covers it.
        
        return None

    def _response(self, text: str) -> Dict[str, Any]:
        return {
            "answer": text,
            "source": "greeting_handler",
            "context_data": {},
            "latency": 0.001 # Extremely fast
        }
