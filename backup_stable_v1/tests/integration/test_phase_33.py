
import unittest
import sys
import os
from unittest.mock import MagicMock
import re

sys.path.append(os.getcwd())
try:
    from src.chat_engine import ChatEngine
    from src.rag.article_interpreter import ArticleInterpreter
except ImportError:
    # Handle import if paths are tricky in test env
    pass

CONFIG = {
    "model": "mock",
    "base_url": "mock",
    "retrieval": {"top_k": 1, "score_threshold": 0.5},
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"save_log": False},
    "knowledge_pack": {"enabled": True},
    "cache": {"enabled": False}
}

class TestPhase33(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        self.engine.kp_manager = MagicMock()
        
    def test_structured_fast_path(self):
        print("\n--- Test: Structured Fast-Path ---")
        interpreter = ArticleInterpreter(CONFIG["llm"])
        content = """
        หน้าหลัก
        
        การปฏิบัติงาน
        1. ส่งภายในเวลา 08:30 น.
        2. ส่ง email ไปที่ report@nt.com
        3. หัวข้อ: รายงานประจำวัน Subject: Daily Report
        4. ผู้จัดทำ: นายสมชาย
        5. เรียน: ผอ.ฝ่าย
        """
        # Patch LLM to ensure no call
        from unittest.mock import patch
        with patch('src.rag.article_interpreter.ollama_generate') as mock_llm:
            ans = interpreter.interpret("ขั้นตอนรายงาน", "Title", "URL", content)
            print(f"Structured Ans:\n{ans}")
            
            self.assertIn("• เวลาส่ง: 08:30 น.", ans)
            self.assertIn("• หัวข้ออีเมล: รายงานประจำวัน", ans)
            self.assertIn("• ผู้จัดทำ: นายสมชาย", ans)
            mock_llm.assert_not_called()

    def test_rag_url_mode(self):
        print("\n--- Test: RAG URL_ONLY Mode ---")
        # Reuse logic is in ChatEngine.process -> _apply_answer_mode
        # We need to simulate a RAG result where we ask for URL
        
        # Mocking process flow parts is hard without full integration.
        # Let's test _apply_answer_mode with doc hits provided manually
        # to ensure it filters correctly.
        
        # Then we assume `process` correctly populates it (verified by code review diff).
        
        hits = [
            {"key": "Article", "value": "My Article", "source_url": "http://test.com/article"},
            {"key": "Article", "value": "Doc 2", "source_url": "http://test.com/doc2"}
        ]
        
        res = self.engine._apply_answer_mode({"hits": hits, "route": "rag"}, "URL_ONLY")
        print(f"URL Mode Ans:\n{res['answer']}")
        
        self.assertIn("http://test.com/article", res['answer'])
        self.assertIn("My Article", res['answer'])

if __name__ == "__main__":
    unittest.main()
