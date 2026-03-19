import unittest
import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.chat_engine import ChatEngine

CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestPhase15AIOrchestration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SETUP] Initializing ChatEngine for Phase 15 Tests...")
        cls.engine = ChatEngine(CFG)
        
    def setUp(self):
        """Reset state before each test"""
        self.engine.last_context = None
        self.engine.pending_clarify = None
        
    def test_phone_only_output_mode(self):
        """Test 'ขอแค่เบอร์ผจ' returns phone-only (no full card)"""
        res = self.engine.process("ขอแค่เบอร์ผจ")
        
        # Must contain phone number
        self.assertIn("074", res["answer"])  # ผจ phone starts with 074
        
        # Must NOT contain full card labels
        self.assertNotIn("ชื่อ:", res["answer"])
        self.assertNotIn("อีเมล:", res["answer"])
        self.assertNotIn("โทรสาร:", res["answer"])
        
        print(f"\n[PASS] Phone-Only Output: {res['answer'][:100]}")
        
    def test_phone_only_followup(self):
        """Test 'ขอแค่เบอร์' after position lookup uses last_context + PHONE_ONLY"""
        # Step 1: Lookup ผจ
        res1 = self.engine.process("ใครคือผจ.สบลตน.")
        self.assertEqual(res1["route"], "position_lookup")
        
        # Step 2: Request phone-only
        res2 = self.engine.process("ขอแค่เบอร์")
        
        # Must use last_context (fast)
        self.assertIn(res2["route"], ["context_followup", "position_lookup"])
        
        # Must contain phone only
        self.assertIn("074", res2["answer"])
        self.assertNotIn("ชื่อ:", res2["answer"])
        
        print(f"\n[PASS] Phone-Only Follow-up: {res2['answer'][:100]}")
        
    def test_multi_turn_clarify_session(self):
        """Test clarify session with slot filling"""
        # Step 1: Trigger clarify
        res1 = self.engine.process("ปัญหา internet ใช้งานไม่ได้")
        self.assertEqual(res1["route"], "rag_clarify")
        
        # Should set pending_clarify
        # Note: This requires ChatEngine process() integration
        # For now, we test that clarify returns fast
        self.assertLess(res1["latencies"]["total"], 1000)
        
        print(f"\n[PASS] Clarify Trigger: {res1['answer'][:100]}")
        
        # Step 2: Reply with symptom (will be implemented after process() integration)
        # res2 = self.engine.process("หลุดบ่อย")
        # self.assertIn("Wi-Fi", res2["answer"])
        # self.assertLess(res2["latencies"]["total"], 1000)
        
    def test_clarify_fast_path(self):
        """Test clarify doesn't call generator/evaluator"""
        res = self.engine.process("ปัญหา internet ใช้งานไม่ได้")
        
        self.assertEqual(res["route"], "rag_clarify")
        self.assertEqual(res["latencies"]["generator"], 0.0)
        self.assertEqual(res["latencies"]["evaluator"], 0.0)
        self.assertEqual(res["latencies"]["llm"], 0.0)
        
        print(f"\n[PASS] Clarify Fast Path: total={res['latencies']['total']:.2f}ms")
        
    def test_email_only_output_mode(self):
        """Test EMAIL_ONLY output mode"""
        # This will work after planner integration
        # For now, test that format_field_only works
        from src.directory.format_answer import format_field_only
        
        data = {
            "name": "Test Person",
            "phones": ["123-456"],
            "emails": ["test@example.com"],
            "faxes": ["789-012"]
        }
        
        result = format_field_only(data, "EMAIL_ONLY", "Test Person")
        self.assertIn("test@example.com", result)
        self.assertNotIn("123-456", result)  # No phone
        
        print(f"\n[PASS] Email-Only Formatter: {result}")

if __name__ == "__main__":
    unittest.main()
