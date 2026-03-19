import unittest
import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestEntityLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine for Entity Tests...")
        cls.chat_engine = ChatEngine(CFG)
        
    def test_role_alias(self):
        print("\n[TEST] Role Alias Resolution")
        # "ผจ" -> Should invoke Position Lookup for "ผจ.สบลตน."
        res = self.chat_engine.process("ผจ")
        print(f"Q: 'ผจ' -> A: {res['answer'][:50]}... Route: {res['route']}")
        self.assertEqual(res["route"], "position_lookup")
        self.assertIn("ปรัชญา", res["answer"]) # Manager Name

    def test_email_request(self):
        print("\n[TEST] Email Request")
        # 1. Set Context
        self.chat_engine.process("ผส.บลตน.")
        
        # 2. Ask Email
        res = self.chat_engine.process("ขออีเมลหน่อย")
        print(f"Q: 'ขออีเมล' -> A: {res['answer']}")
        self.assertEqual(res["route"], "context_followup_miss")
        self.assertIn("ไม่มีข้อมูลอีเมล", res["answer"])

if __name__ == "__main__":
    unittest.main()
