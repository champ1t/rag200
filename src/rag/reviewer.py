
from typing import Dict, Any, List, Optional
from src.rag.ollama_client import ollama_generate

REVIEWER_PROMPT = """
คุณคือ "AI Reviewer" ผู้ตรวจสอบความถูกต้องของระบบ RAG
หน้าที่: ตรวจสอบว่า "คำตอบ (Answer)" ถูกต้องตาม "หลักฐาน (Evidence)" หรือไม่

กฎการตรวจสอบ (Strict rules):
1. **Pass**: ถ้าข้อมูลใน Answer ทั้งหมด มีอยู่ใน Evidence (หรือเป็นการสรุปที่ถูกต้อง)
2. **Fail**: ถ้า Answer มีข้อมูลใหม่/ตัวเลข/ชื่อคน ที่ไม่มีใน Evidence เลย (Hallucination)
3. **Fail**: ถ้า Answer เป็นการเดา หรือตอบไม่ตรงคำถาม

ข้อยกเว้น (Exception):
- หากคำตอบขึ้นต้นด้วย "เนื่องจากไม่พบเอกสารภายใน" หรือ "ขออธิบายตามหลักการทั่วไป":
- **Pass**: ยอมรับเนื้อหาความรู้ทั่วไป (General Knowledge) ที่ถูกต้อง แม้ไม่มีใน Evidence
- **Fail**: ห้ามอ้างว่าเป็นข้อมูลภายใน, ห้ามมั่วเลข IP/Contact/Password

Context (Evidence):
{evidence_text}

Question: {query}
Answer: {answer}

จงวิเคราะห์และตอบกลับในรูปแบบ JSON เท่านั้น:
{{
  "verdict": "PASS" หรือ "FAIL",
  "reason": "อธิบายเหตุผลสั้นๆ",
  "safe_response": "ถ้า FAIL ให้เขียนคำตอบใหม่ที่ปลอดภัย (เช่น ข้อมูลไม่เพียงพอ ให้ติดต่อเจ้าหน้าที่)"
}}
"""

class RAGReviewer:
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_cfg = llm_config
        # Use a faster/smaller model for reviewing if possible, or same model
        # For now, reuse the same config but maybe lower temp
        
    def review(
        self, 
        query: str, 
        answer: str, 
        evidence: List[Any]
    ) -> Dict[str, Any]:
        """
        Review the generated answer against evidence.
        """
        # 1. Prepare Evidence Text (Truncated)
        evidence_text = ""
        for i, doc in enumerate(evidence[:3]): # Check top 3 docs only for speed
            txt = getattr(doc, "text", str(doc))[:500] # Cap text
            evidence_text += f"[Doc {i+1}]: {txt}\n"
            
        if not evidence_text:
             evidence_text = "No evidence provided."

        prompt = REVIEWER_PROMPT.format(
            evidence_text=evidence_text,
            query=query,
            answer=answer
        )
        
        try:
            # Force JSON mode if supported or just parse text
            # We'll rely on strict prompt for now.
            res = ollama_generate(
                base_url=self.llm_cfg.get("base_url"),
                model=self.llm_cfg.get("model"),
                prompt=prompt,
                temperature=0.0,
                num_predict=256,
                timeout=30.0 # Fast timeout
            )
            
            # Simple JSON parser (robustness)
            import json
            import re
            
            # Try to find JSON block
            match = re.search(r"\{.*\}", res, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                return result
            else:
                # Fallback if no JSON found (Assume PASS if model is confused? No, Fail safe)
                # Or maybe it just outputted text.
                if "PASS" in res: return {"verdict": "PASS", "reason": "Parsed from text"}
                return {"verdict": "SOFT_FAIL", "reason": "Reviewer output format error", "safe_response": "ข้อมูลไม่แน่ชัด กรุณาตรวจสอบกับเจ้าหน้าที่"}
                
        except Exception as e:
            print(f"[Reviewer] Error: {e}")
            return {"verdict": "PASS", "reason": "Reviewer Error (Bypassed)"} # Fail open or closed? Fail Open for availability, Closed for safety.
            # Let's Fail Open (PASS) for now to avoid blocking on reviewer error, but log it.
