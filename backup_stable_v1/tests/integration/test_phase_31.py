
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())
from src.chat_engine import ChatEngine

# Mock config
CONFIG = {
    "model": "mock",
    "base_url": "mock",
    "retrieval": {"top_k": 1, "score_threshold": 0.5},
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"save_log": False},
    "knowledge_pack": {"enabled": True},
    "cache": {"enabled": False}
}

class TestPhase31(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        
        # Mock KP Manager
        self.engine.kp_manager = MagicMock()
        
    def test_multi_key_aggregation(self):
        print("\n--- Test: Multi-Key KP Aggregation ---")
        # Setup mock returns
        def side_effect(q):
            if "dns" in q.lower():
                return {"answer": "DNS Info", "hits": [{"key": "DNS"}], "signal": "FOUND"}
            if "smtp" in q.lower():
                return {"answer": "SMTP Info", "hits": [{"key": "SMTP"}], "signal": "FOUND"}
            return None
            
        self.engine.kp_manager.lookup.side_effect = side_effect
        
        # Test Query
        res = self.engine.process("DNS and SMTP")
        
        self.assertIn("=== DNS ===", res["answer"])
        self.assertIn("DNS Info", res["answer"])
        self.assertIn("=== SMTP ===", res["answer"])
        self.assertIn("SMTP Info", res["answer"])
        print(f"Aggregated Answer:\n{res['answer']}")

    def test_strict_exec_filter(self):
        from src.rag.article_cleaner import extract_executive_list
        print("\n--- Test: Strict Executive Filter ---")
        content = """
        รายชื่อผู้บริหาร
        1. นาย ก (ผจก.)
        2. ผจ.สบลตน. (Itemid=123)
        3. นาง ข (ผส.)
        4. com_wrapper view=category
        """
        execs = extract_executive_list(content)
        print(f"Extracted: {execs}")
        
        self.assertEqual(len(execs), 2)
        self.assertTrue(any("นาย ก" in e for e in execs))
        self.assertTrue(any("นาง ข" in e for e in execs))
        self.assertFalse(any("Itemid" in e for e in execs))

    def test_procedural_fast_path(self):
        print("\n--- Test: Procedural Fast-Path ---")
        # Reuse logic is in Interpreter, let's test Interpreter directly?
        # Requires mocking ArticleInterpreter dependencies.
        # Let's verify by checking if ChatEngine calls LLM or not?
        # Checking logic via unit test on interpreter instance is better.
        
        from src.rag.article_interpreter import ArticleInterpreter
        interpreter = ArticleInterpreter(CONFIG["llm"])
        
        # Mock content that triggers fast path
        content = """
        หน้าหลัก
        
        การจัดทำรายงาน
        1. ส่งภายในเวลา 08:30 น.
        2. ส่ง email ไปที่ admin@nt.com
        3. หัวข้อ: รายงานประจำวัน
        4. ใช้แบบฟอร์มล่าสุด
        """
        
        # Interpret
        # We need to mock ollama_generate to ensure it's NOT called
        from unittest.mock import patch
        with patch('src.rag.article_interpreter.ollama_generate') as mock_llm:
            ans = interpreter.interpret("ขั้นตอนรายงาน", "Title", "URL", content)
            
            mock_llm.assert_not_called()
            self.assertIn("08:30 น.", ans)
            self.assertIn("admin@nt.com", ans)
            print(f"Fast-Path Answer:\n{ans}")

if __name__ == "__main__":
    unittest.main()
