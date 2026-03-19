
from typing import List, Dict, Any, Optional

class SafetyGuard:
    @staticmethod
    def check_retrieval_safety(hits: List[Any]) -> Dict[str, Any]:
        """
        Kill-Switch: Check if retrieval results are safe to generate from.
        Returns: { "safe": bool, "reason": str }
        """
        if not hits:
            return {"safe": False, "reason": "No hits found"}

        # 1. Low Score Guard (Re-using R1 threshold logic usually, but enforcing strict stop here)
        # If TOP 1 score is < 0.35, it's garbage.
        top_score = getattr(hits[0], "score", 0.0)
        if top_score < 0.20:
            return {"safe": False, "reason": f"Top score too low ({top_score:.2f} < 0.20)"}

        # 2. Navigation/Boilerplate Guard
        # If top result is a known login/home page without specific content
        top_meta = getattr(hits[0], "metadata", {}) or {}
        top_title = top_meta.get("title", "").lower()
        top_url = top_meta.get("url", "").lower() or top_meta.get("source", "").lower()
        
        BOILERPLATE_TITLES = ["home", "login", "เข้าสู่ระบบ", "หน้าหลัก", "main menu"]
        BOILERPLATE_URLS = ["/login", "/home", "/index.php", "view=category"]
        
        if any(b == top_title for b in BOILERPLATE_TITLES):
             return {"safe": False, "reason": f"Boilerplate Title Detected: {top_title}"}
             
        if any(b in top_url for b in BOILERPLATE_URLS) and len(hits) < 2:
             # Single hit and it's a nav page -> Unsafe
             return {"safe": False, "reason": f"Nav Page Detected: {top_url}"}

        # 3. Context Anaemia Guard
        # If total context length is suspiciously short
        total_len = sum(len(getattr(h, "text", "")) for h in hits)
        if total_len < 200:
             return {"safe": False, "reason": f"Insufficient Context Length ({total_len} chars)"}

        return {"safe": True, "reason": "OK"}
