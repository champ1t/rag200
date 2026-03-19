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
    "rag": {"score_threshold": 0.25, "use_cache": False}, # Cache irrelevant for follow-up logic test
    "chat": {"show_context": False, "save_log": False}
}

class TestClarifyDetail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing Engine...")
        cls.engine = ChatEngine(CFG)
        cls.engine.router = MagicMock()
        cls.engine.corrector = MagicMock()
        cls.engine.corrector.correct.return_value = None
        cls.engine.cache = MagicMock()
        cls.engine.directory_handler = MagicMock()

    def setUp(self):
        self.engine.pending_question = None
        self.engine.directory_handler.reset_mock()
        self.engine.directory_handler.handle_management_query.return_value = {"answer": "HOLDER_INFO", "route": "lookup"}

    def test_detail_single_candidate(self):
        """Test 'ชื่อเต็ม' auto-selects if only 1 candidate."""
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [{"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."}],
            "mode": "holder",
            "created_at": time.time()
        }
        
        # Action
        res = self.engine.process("ชื่อเต็ม")
        
        # Assert
        self.assertEqual(res["answer"], "HOLDER_INFO")
        self.assertIsNone(self.engine.pending_question)
        self.engine.directory_handler.handle_management_query.assert_called_with("ผส.บลตน.")

    def test_detail_multi_candidate_reask(self):
        """Test 'ชื่อเต็ม' asks for number if multiple candidates."""
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [
                {"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."},
                {"id": 2, "label": "ผส.พพ.", "key": "ผส.พพ."}
            ],
            "mode": "holder",
            "created_at": time.time()
        }
        
        # Action
        res = self.engine.process("ขอชื่อเต็ม")
        
        # Assert
        self.assertIn("ต้องการข้อมูลเต็มของข้อไหนครับ", res["answer"])
        self.assertEqual(res["route"], "followup_reask")
        self.assertIsNotNone(self.engine.pending_question, "Should remain pending")

    def test_detail_specific_fuzzy(self):
        """Test 'ชื่อเต็ม ผส.บลตน.' selects specific candidate using fuzzy logic."""
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [
                {"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."},
                {"id": 2, "label": "ผส.พพ.", "key": "ผส.พพ."}
            ],
            "mode": "holder",
            "created_at": time.time()
        }
        
        # Action
        res = self.engine.process("ขอชื่อเต็ม ผส.บลตน.")
        
        # Assert
        self.assertEqual(res["answer"], "HOLDER_INFO")
        self.assertIsNone(self.engine.pending_question)
        self.engine.directory_handler.handle_management_query.assert_called_with("ผส.บลตน.")

    def test_cancel_logic(self):
        """Test 'ไม่' cancels."""
        self.engine.pending_question = {
            "kind": "role_choice",
            "candidates": [{"id": 1, "label": "X"}],
            "created_at": time.time()
        }
        res = self.engine.process("ไม่")
        self.assertEqual(res["route"], "followup_cancel")
        self.assertIsNone(self.engine.pending_question)

    def test_regression_holder_fullname(self):
        """Regression: ['ใครคือ ผส.', 'ชื่อเต็ม'] -> Full holder details."""
        # Turn 1: Ambiguous query
        self.engine.router.route.return_value = {"intent": "CLARIFY", "confidence": 0.9}
        self.engine.directory_handler.suggest_roles.return_value = ["ผส.บลตน."]
        
        res1 = self.engine.process("ใครคือ ผส.")
        self.assertIn("1) ผส.บลตน.", res1["answer"])
        self.assertIsNotNone(self.engine.pending_question)
        
        # Turn 2: Detail request with single candidate
        res2 = self.engine.process("ชื่อเต็ม")
        self.assertEqual(res2["answer"], "HOLDER_INFO")
        self.assertIsNone(self.engine.pending_question)

    def test_regression_phone_confirm(self):
        """Regression: ['เบอร์ ผส.', 'ใช่'] -> Phone number."""
        # Turn 1: Ambiguous phone query
        self.engine.router.route.return_value = {"intent": "CLARIFY", "confidence": 0.9}
        self.engine.directory_handler.suggest_roles.return_value = ["ผส.บลตน."]
        
        res1 = self.engine.process("เบอร์ ผส.")
        self.assertIn("1) ผส.บลตน.", res1["answer"])
        self.assertEqual(self.engine.pending_question["mode"], "phone")
        
        # Turn 2: Confirm with single candidate
        with patch("src.rag.handlers.contact_handler.ContactHandler.handle") as mock_contact:
            mock_contact.return_value = {"answer": "Phone: 02-123-4567", "route": "contact_lookup"}
            res2 = self.engine.process("ใช่")
            self.assertIn("Phone:", res2["answer"])
            self.assertIsNone(self.engine.pending_question)

    def test_regression_multi_candidate_detail(self):
        """Regression: ['ใครคือ ผจ.', 'ชื่อเต็ม'] -> Re-ask if multiple candidates."""
        # Turn 1: Ambiguous query with multiple results
        self.engine.router.route.return_value = {"intent": "CLARIFY", "confidence": 0.9}
        self.engine.directory_handler.suggest_roles.return_value = ["ผจ.บลตน.", "ผจ.พพ.", "ผจ.รกภ."]
        
        res1 = self.engine.process("ใครคือ ผจ.")
        self.assertIn("1) ผจ.บลตน.", res1["answer"])
        self.assertIsNotNone(self.engine.pending_question)
        
        # Turn 2: Detail request with multiple candidates
        res2 = self.engine.process("ชื่อเต็ม")
        self.assertIn("ต้องการข้อมูลเต็มของข้อไหนครับ", res2["answer"])
        self.assertEqual(res2["route"], "followup_reask")
        self.assertIsNotNone(self.engine.pending_question, "Should remain pending")

if __name__ == "__main__":
    unittest.main()
