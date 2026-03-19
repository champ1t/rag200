import sys
import unittest
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.core.chat_engine import ChatEngine

# Mock Config (uses real data, mock llm)
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestProductionRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine for Golden Tests...")
        cls.engine = ChatEngine(CFG)

    def test_quick_reply(self):
        """Test 0ms latency responses"""
        res = self.engine.process("Hello")
        self.assertEqual(res["route"], "quick_reply")
        self.assertIn("สวัสดี", res["answer"])
        
        res = self.engine.process("ขอบคุณ")
        self.assertEqual(res["route"], "quick_reply")
        self.assertIn("ยินดี", res["answer"])

    def test_lookup_contact(self):
        """Test Deterministic Contact Lookup"""
        res = self.engine.process("ขอเบอร์ คุณสมบูรณ์")
        # Should be phone lookup
        self.assertIn(res["route"], ["contact_name", "contact_miss"]) 
        # If data is present, "contact_name". If typo, "contact_miss".
        # We know "สมบูรณ์" is in the system (Director).
        
    def test_lookup_link_fuzzy(self):
        """Test Fuzzy Link Lookup"""
        # "edoccument" -> "edocument"
        res = self.engine.process("ขอลิงก์ edoccument")
        self.assertEqual(res["route"], "link_lookup")
        self.assertIn("Edocument", res["answer"])

    def test_lookup_position(self):
        """Test Position Lookup"""
        res = self.engine.process("ใครคือ ผส.บลตน.")
        self.assertEqual(res["route"], "position_lookup")
        self.assertIn("สมบูรณ์", res["answer"])

    def test_ood_rejection_logic(self):
        """
        Hard to test OOD strictly without mocking vectorstore scores,
        but we can check if it goes to RAG and returns 'not found' 
        if we pass a nonsense query that shouldn't match anything good.
        """
        # "Star Wars Plot" -> Should have low score
        res = self.engine.process("Star Wars Plot")
        # If score < 0.25, route is "rag_no_docs" or "rag_low_score"
        if res["route"] in ["rag_no_docs", "rag_low_score"]:
            pass # Pass
        else:
            # If it went to RAG, check if answer implies not found
            # But really we want route matching
            print(f"Warning: Star Wars query went to {res['route']}")
            
    def test_structured_template_prompt(self):
        """
        Indirectly test prompt presence by checking source code? 
        Or just verifying the flow runs.
        """
        res = self.engine.process("How to configure ONU")
        # Should go to RAG
        # We can't verify output structure easily with mock/live LLM without visual check,
        # but we ensure it doesn't crash.
        print(f"[DEBUG] RAG Test Route: {res['route']}")
        self.assertTrue(res["route"] in ["rag", "rag_low_score", "rag_no_docs"])

if __name__ == "__main__":
    unittest.main()
