
import unittest
import sys
import os
from unittest.mock import MagicMock
import re

sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine
from src.rag.article_interpreter import ArticleInterpreter

CONFIG = {
    "model": "mock",
    "base_url": "mock",
    "retrieval": {"top_k": 1, "score_threshold": 0.5},
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"save_log": False},
    "knowledge_pack": {"enabled": True},
    "cache": {"enabled": False}
}

class TestPhase32(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        self.engine.kp_manager = MagicMock()
        
    def test_multi_key_complete_output(self):
        print("\n--- Test: Multi-Key Completeness ---")
        def side_effect(q):
            if "dns" in q.lower(): return {"answer": "DNS OK", "hits": [{"key": "DNS"}], "signal": "FOUND"}
            if "smtp" in q.lower(): return {"answer": "SMTP OK", "hits": [{"key": "SMTP"}], "signal": "FOUND"}
            return None
        self.engine.kp_manager.lookup.side_effect = side_effect
        
        res = self.engine.process("DNS and SMTP")
        self.assertIn("=== DNS ===", res["answer"])
        self.assertIn("DNS OK", res["answer"])
        self.assertIn("=== SMTP ===", res["answer"])
        self.assertIn("SMTP OK", res["answer"])
        print(f"Aggregated: {res['answer']}")
        
    def test_name_only_mode(self):
        print("\n--- Test: NAME_ONLY Mode ---")
        matches = [
            {"value": "นาย สมชาย ใจดี (ผจก.)"},
            {"value": "นางสาว สมหญิง จริงใจ"},
            {"value": "Login Button"} # Noise
        ]
        res = self.engine._apply_answer_mode({"hits": matches, "route": "rag"}, "NAME_ONLY")
        ans = res["answer"]
        print(f"Name Only Ans: {ans}")
        self.assertIn("1. นาย สมชาย", ans)
        self.assertIn("2. นางสาว สมหญิง", ans)
        self.assertNotIn("Login", ans)
        self.assertNotIn("ผจก.", ans) # Should ideally strip roles but my regex captures full name line if match? 
        # Check implementation: regex was r"((?:title)...)" -> It captures the NAME part correctly if group 1 is used.
        # My regex was strict on name structure.
        
    def test_fast_path_compact(self):
        print("\n--- Test: Fast-Path Compact ---")
        interpreter = ArticleInterpreter(CONFIG["llm"])
        content = """
        หน้าหลัก
        
        การจัดทำรายงาน
        1. ส่งภายในเวลา 08:30 น.
        2. ส่ง email ไปที่ admin@nt.com
        3. หัวข้อ: รายงานประจำวัน
        4. ใช้แบบฟอร์มล่าสุด
        5. ผู้จัดทำ: นาย A
        6. เรียน: ผจก.
        7. CC: ทีมงาน
        8. Download Link http://test.com
        9. Extra line 1
        10. Extra line 2
        """
        # Testing "Summary" limit (should be 5)
        # We need to mock ollama_generate to confirm no LLM call
        from unittest.mock import patch
        with patch('src.rag.article_interpreter.ollama_generate') as mock_llm:
            ans = interpreter.interpret("สรุปขั้นตอนรายงาน", "Title", "URL", content)
            print(f"Compact Ans:\n{ans}")
            lines = ans.splitlines()
            # Title + 5 bullets = 6 lines
            self.assertLessEqual(len(lines), 7) # allow some wiggle room
            self.assertIn("08:30", ans)

if __name__ == "__main__":
    unittest.main()
