import unittest
import sys
import os
import time
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25, "use_cache": True},
    "chat": {"show_context": False, "save_log": False}
}

class TestCacheBypass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine...")
        cls.engine = ChatEngine(CFG)
        
        # Mock Cache
        cls.engine.cache = MagicMock()
        # Setup Cache to ALWAYS return a hit to verify bypass logic
        cls.engine.cache.check.return_value = {
            "answer": "CACHED_ANSWER", 
            "score": 1.0, 
            "latency": 0.1
        }
        
        # Mock Router to always force Fallback/RAG 
        # (Where cache logic lives)
        cls.engine.router = MagicMock()
        cls.engine.router.route.return_value = {"intent": "GENERAL_QA", "confidence": 0.5}
        
        # Mock Controller to avoid LLM calls
        cls.engine.controller = MagicMock()
        cls.engine.controller.decide.return_value = {"strategy": "NO_ANSWER", "reason": "Mocked"}
        
        # Mock Corrector
        cls.engine.corrector = MagicMock()
        cls.engine.corrector.correct.return_value = None # No correction

    def setUp(self):
        self.engine.pending_question = None

    def test_bypass_short_followup(self):
        """Test simple short tokens like 'Yes' bypass cache."""
        # Query = "ใช่" (Short)
        # Should bypass cache check -> Fall through to RAG/Controller -> Mocked NO_ANSWER
        # If it hit cache, answer would be "CACHED_ANSWER"
        
        res = self.engine.process("ใช่ครับ")
        
        print(f"[Result]: {res['answer']}")
        
        # Verify result is NOT "CACHED_ANSWER"
        self.assertNotEqual(res["answer"], "CACHED_ANSWER", "Should have bypassed cache!")
        # It might be no_docs because we didn't mock VS results
        self.assertIn(res["route"], ["rag_controller_rejected", "rag_no_docs"])

    def test_bypass_pending_state(self):
        """Test pending question state bypasses cache."""
        # Set pending question state (simulating unrelated query during clarify)
        self.engine.pending_question = {
            "kind": "mock", 
            "candidates": [], 
            "created_at": time.time()
        }
        
        # Query = "Some random text" (Longer than short check)
        # But pending state exists -> Should bypass
        res = self.engine.process("Some random text query that is long")
        
        print(f"[Result]: {res['answer']}")
        self.assertNotEqual(res["answer"], "CACHED_ANSWER", "Should have bypassed cache due to pending state!")
        
    def test_hit_cache_normal(self):
        """Test normal query hits cache."""
        self.engine.pending_question = None
        
        res = self.engine.process("Normal Query")
        
        self.assertEqual(res["answer"], "CACHED_ANSWER")
        self.assertEqual(res["route"], "cache_hit")

if __name__ == "__main__":
    unittest.main()
