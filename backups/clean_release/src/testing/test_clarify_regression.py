import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25, "use_cache": True}, # Important: Enable cache
    "chat": {"show_context": False, "save_log": False}
}

class TestClarifyRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine for Regression...")
        cls.engine = ChatEngine(CFG)
        
        # Mocks
        cls.engine.router = MagicMock()
        cls.engine.corrector = MagicMock()
        cls.engine.corrector.correct.return_value = None
        cls.engine.cache = MagicMock()
        cls.engine.directory_handler = MagicMock()
        
        # Default Behaviors
        cls.engine.cache.check.return_value = {"answer": "CACHED_WRONG_ANSWER", "score": 1.0, "latency": 10.0}
        cls.engine.directory_handler.suggest_roles.return_value = []
        cls.engine.directory_handler.suggest_teams.return_value = []
        cls.engine.directory_handler.suggest_persons.return_value = []

    def setUp(self):
        self.engine.pending_question = None
        self.engine.cache.reset_mock()
        self.engine.router.reset_mock()
        self.engine.directory_handler.reset_mock()
        
        # Reset default mocks
        self.engine.cache.check.return_value = {"answer": "CACHED_WRONG_ANSWER", "score": 1.0, "latency": 10.0}
        self.engine.directory_handler.suggest_roles.return_value = []

    def test_clarify_never_cache(self):
        """1) test_clarify_never_cache: CLARIFY intent must bypass cache."""
        # Setup: Router detects CLARIFY
        self.engine.router.route.return_value = {"intent": "CLARIFY", "confidence": 0.9, "reason": "Ambiguous"}
        
        # Setup: Directory suggests candidates
        self.engine.directory_handler.suggest_roles.return_value = ["ผส.บลตน.", "ผส.พพ."]
        
        # Action
        res = self.engine.process("ใครคือ ผส.")
        
        # Assert
        # Should NOT return cached answer
        self.assertNotEqual(res["answer"], "CACHED_WRONG_ANSWER")
        # Should return formatted list
        self.assertIn("1) ผส.บลตน.", res["answer"])
        # Route should be clarify variant
        self.assertEqual(res["route"], "clarify_ambiguous")
        # Pending question should be set
        self.assertIsNotNone(self.engine.pending_question)
        self.assertEqual(self.engine.pending_question["mode"], "holder") # "ใครคือ" -> holder

    def test_followup_yes_resolves(self):
        """2) test_followup_yes_resolves: Selecting '1' resolves to correct info."""
        # Setup: Pending Question State
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [{"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."}],
            "mode": "phone",
            "created_at": time.time(),
            "original_query": "เบอร์ ผส."
        }
        
        # Mock ContactHandler (via patch or if it's imported inside method, we mock the method call result)
        # Since ContactHandler.handle is static and imported inside, we patch it decorator style or context
        with patch("src.rag.handlers.contact_handler.ContactHandler.handle") as mock_contact:
            mock_contact.return_value = {"answer": "Phone: 02-123-4567", "route": "contact_lookup"}
            
            # Action
            res = self.engine.process("1") # User selects 1
            
            # Assert
            self.assertEqual(res["answer"], "Phone: 02-123-4567")
            self.assertEqual(res["route"], "contact_lookup")
            self.assertIsNone(self.engine.pending_question)
            
            # Verify correct query passed to ContactHandler "เบอร์โทร ผส.บลตน."
            args, _ = mock_contact.call_args
            self.assertIn("เบอร์โทร ผส.บลตน.", args[0])

    def test_followup_negative(self):
        """3) test_followup_wrong_token: saying 'no' cancels or asks retry."""
        # Setup: Pending Question State
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [{"id": 1, "label": "X"}],
            "mode": "phone",
            "created_at": time.time()
        }
        
        # Action
        res = self.engine.process("ไม่")
        
        # Assert
        self.assertEqual(res["route"], "followup_cancel")
        self.assertIsNone(self.engine.pending_question)
        self.assertIn("ยกเลิก", res["answer"])

    def test_non_clarify_cache_ok(self):
        """4) test_non_clarify_cache_ok: Normal query hits cache."""
        # Setup: Ensure Router returns standard intent so it falls through to Cache
        self.engine.router.route.return_value = {"intent": "GENERAL_QA", "confidence": 1.0}
        
        # Action
        res = self.engine.process("เบอร์ Radius NT1")
        
        # Assert
        self.assertEqual(res["answer"], "CACHED_WRONG_ANSWER")
        # Router was called
        self.engine.router.route.assert_called()

if __name__ == "__main__":
    unittest.main()
