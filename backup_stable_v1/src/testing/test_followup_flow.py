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
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestFollowUpFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine...")
        cls.engine = ChatEngine(CFG)
        
        # Mock Directory Handler to force ambiguity
        cls.engine.directory_handler = MagicMock()
        
        # Mock Router and Corrector
        cls.engine.router = MagicMock()
        cls.engine.corrector = MagicMock()
        
        # Default Intent Logic
        def route_side_effect(q):
            if "เบอร์" in q and "ผส" in q:
                return {"intent": "MANAGEMENT_LOOKUP", "confidence": 0.9}
            return {"intent": "GENERAL_QA", "confidence": 0.5}
            
        cls.engine.router.route.side_effect = route_side_effect
        
        # Scenario 1: Mock Management Query "เบอร์ ผส." -> Returns Ambiguous
        cls.ambiguous_res = {
            "answer": "Ambiguous Choice",
            "route": "management_ambiguous",
            "candidates": [
                {"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."},
                {"id": 2, "label": "ผส.พพ.", "key": "ผส.พพ."}
            ],
            "original_query": "เบอร์ ผส."
        }
        cls.engine.directory_handler.handle_management_query.return_value = cls.ambiguous_res
        
        # Use side_effect to return specific result based on query
        def side_effect(q):
            if "ผส.บลตน." in q: 
                return {"answer": "Found ผส.บลตน.", "route": "position_lookup", "hits": [{"name": "Somchai"}]}
            return cls.ambiguous_res
            
        cls.engine.directory_handler.handle_management_query.side_effect = side_effect

    def setUp(self):
        # Reset state
        self.engine.pending_question = None

    def test_ambiguity_trigger(self):
        """Test that ambiguity triggers pending question state."""
        # 1. User asks ambiguous query
        res = self.engine.process("เบอร์ ผส.")
        print(f"[Result]: {res['route']}")
        
        self.assertEqual(res["route"], "management_ambiguous")
        self.assertIsNotNone(self.engine.pending_question, "Should set pending_question")
        self.assertEqual(len(self.engine.pending_question["candidates"]), 2)
        print(f"[Test Trigger]: {self.engine.pending_question}")

    def test_resolve_by_number(self):
        """Test resolving by typing '1'."""
        # Setup state
        self.engine.pending_question = {
            "kind": "management_choice",
            "candidates": [
                {"id": 1, "label": "ผส.บลตน.", "key": "ผส.บลตน."},
                {"id": 2, "label": "ผส.พพ.", "key": "ผส.พพ."}
            ],
            "original_query": "เบอร์ ผส.",
            "created_at": time.time()
        }
        
        # User types "เลือกข้อ 1"
        res = self.engine.process("เลือกข้อ 1 ครับ")
        
        self.assertEqual(res["answer"], "Found ผส.บลตน.") # Mocked response
        self.assertIsNone(self.engine.pending_question, "Should clear state")
        print(f"[Test Number]: Resolved to {res['answer']}")

    def test_resolve_yes_logic(self):
        """Test 'Yes' logic (Re-ask if multiple)."""
        # Setup state (2 candidates)
        self.engine.pending_question = {
            "kind": "management_choice",
            "candidates": [
                {"id": 1, "label": "A", "key": "A"},
                {"id": 2, "label": "B", "key": "B"}
            ],
            "original_query": "Q",
            "created_at": time.time()
        }
        
        # User types "ใช่ครับ"
        # Should NOT resolve (which one?)
        res = self.engine.process("ใช่ครับ")
        
        self.assertEqual(res["route"], "followup_reask", "Should ask which one")
        self.assertIn("หมายถึงข้อไหน", res["answer"])
        self.assertIsNotNone(self.engine.pending_question, "Should KEEP state")
        
    def test_cancel(self):
        """Test 'No' cancels."""
        self.engine.pending_question = {"candidates": [], "created_at": time.time()}
        res = self.engine.process("ไม่ครับ")
        self.assertEqual(res["route"], "followup_cancel")
        self.assertIsNone(self.engine.pending_question)

if __name__ == "__main__":
    unittest.main()
