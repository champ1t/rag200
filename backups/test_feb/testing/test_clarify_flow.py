import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25, "use_cache": True}, # Enable cache to test bypass
    "chat": {"show_context": False, "save_log": False}
}

class TestClarifyFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine...")
        cls.engine = ChatEngine(CFG)
        
        # Mock Router to simulate CLARIFY intent
        cls.engine.router = MagicMock()
        cls.engine.corrector = MagicMock()
        cls.engine.corrector.correct.return_value = None
        
        # Mock Cache to always return hit (to test bypass)
        cls.engine.cache = MagicMock()
        cls.engine.cache.check.return_value = {"answer": "CACHED_WRONG", "score": 1.0, "latency": 0.1}
        
        # Mock Directory Handler for Ambiguity
        cls.engine.directory_handler = MagicMock()
        
        # Mock suggestions
        cls.engine.directory_handler.suggest_roles.return_value = ["ผส.บลตน.", "ผส.พพ."]
        cls.engine.directory_handler.suggest_teams.return_value = []
        cls.engine.directory_handler.suggest_persons.return_value = []

    def setUp(self):
        self.engine.pending_question = None

    def test_clarify_bypass_cache(self):
        """Test that intent='CLARIFY' bypasses the cache."""
        # Setup Router to return CLARIFY
        self.engine.router.route.return_value = {
            "intent": "CLARIFY", 
            "confidence": 0.9, 
            "reason": "Ambiguous"
        }
        
        # Query
        res = self.engine.process("เบอร์ ผส.")
        
        # Expectation: 
        # 1. Should NOT return "CACHED_WRONG"
        # 2. Should return deterministic string "1) ... 2) ..."
        # 3. Should set pending_question with mode="phone"
        
        self.assertNotEqual(res["answer"], "CACHED_WRONG", "Should bypass cache on CLARIFY intent")
        self.assertIn("1) ผส.บลตน.", res["answer"])
        self.assertIn("2) ผส.พพ.", res["answer"])
        
        pq = self.engine.pending_question
        self.assertIsNotNone(pq)
        self.assertEqual(pq["mode"], "phone")
        print(f"[Test 1] Passed: Mode={pq['mode']}")

    @patch("src.rag.handlers.contact_handler.ContactHandler.handle")
    def test_resolve_phone_mode(self, mock_contact_handle):
        """Test resolving a 'phone' mode pending question calls ContactHandler."""
        # Setup State
        self.engine.pending_question = {
            "kind": "management_choice",
            "candidates": [
                {"id": 1, "label": "Somchai", "key": "Somchai"}
            ],
            "mode": "phone",
            "created_at": time.time()
        }
        
        # Mock ContactHandler return
        mock_contact_handle.return_value = {"answer": "Phone is 1234", "route": "contact_lookup"}
        
        # Execute Resolution
        res = self.engine.process("เลือกข้อ 1")
        
        # Verify
        mock_contact_handle.assert_called_once()
        args, _ = mock_contact_handle.call_args
        self.assertIn("เบอร์โทร Somchai", args[0])
        
        self.assertEqual(res["answer"], "Phone is 1234")
        self.assertIsNone(self.engine.pending_question)
        print("[Test 2] Passed: Called ContactHandler properly")

if __name__ == "__main__":
    unittest.main()
