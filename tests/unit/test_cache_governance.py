
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

class TestCacheGovernance(unittest.TestCase):
    def setUp(self):
        # Mock Config
        self.config = {
            "model": "mock",
            "base_url": "mock",
            "retrieval": {"top_k": 1, "score_threshold": 0.5},
            "llm": {"model": "mock", "base_url": "mock"},
            "chat": {"save_log": False},
            "knowledge_pack": {"enabled": False},
            "cache": {"enabled": True}  # Enable Cache
        }
        self.engine = ChatEngine(self.config)
        self.engine.warmup()
        
        # Mock Cache
        self.engine.cache = MagicMock()
        
        # Mock Vector Store (to verify fall-through)
        self.engine.vs = MagicMock()
        self.engine.vs.query.return_value = [] # Return empty to distinguish from cache hit
        self.engine.vs.hybrid_query.return_value = []

    def test_accept_valid_cache(self):
        # Setup: Valid Cache (Has Sources)
        self.engine.cache.check.return_value = {
            "answer": "Answer text here. แหล่งข้อมูลอ้างอิง: 1. URL",
            "score": 0.9,
            "latency": 10,
            "sources": [{"url": "http://example.com", "title": "Test"}]
        }
        
        res = self.engine.process("test query")
        
        self.assertEqual(res["route"], "cache_hit")
        self.assertIn("แหล่งข้อมูลอ้างอิง:", res["answer"])

    def test_reject_missing_refs_long_answer(self):
        # Setup: Invalid Cache (Long answer but NO Sources)
        long_ans = "This is a very long answer that should definitely have sources attached to it if it verified content." * 5
        self.engine.cache.check.return_value = {
            "answer": long_ans,
            "score": 0.9,
            "latency": 10,
            # No sources in text
        }
        
        # Call process
        res = self.engine.process("test query")
        
        # Should NOT be cache_hit
        self.assertNotEqual(res["route"], "cache_hit")
        
        # Should have called VS (Fallthrough)
        # Note: ChatEngine calls hybrid_query or query. My mock supports both implicitly via MagicMock but let's check
        # verification.
        # ChatEngine initialization might not have set hybrid_query on mock vs if checks exist.
        # But `process` checks `hasattr(self.vs, "hybrid_query")`. MagicMock has all attributes.
        self.engine.vs.hybrid_query.assert_called_once()
        
    def test_accept_short_answer_without_refs(self):
        # Setup: Short answer (e.g. Greeting)
        self.engine.cache.check.return_value = {
            "answer": "สวัสดีครับ",
            "score": 0.9,
            "latency": 5
        }
        
        res = self.engine.process("short query")
        
        # Should persist (Short answers don't need sources)
        self.assertEqual(res["route"], "cache_hit")

if __name__ == "__main__":
    unittest.main()
