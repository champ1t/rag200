import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestContextRefinement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine for Refinement Tests...")
        cls.chat_engine = ChatEngine(CFG)
        
    def test_position_ask_link(self):
        print("\n[TEST] Position -> Ask Link")
        # 1. Ask Position "ผส.บลตน." (known to have source)
        self.chat_engine.process("ผส.บลตน.")
        
        # 2. Ask Link "ขอลิงก์"
        res = self.chat_engine.process("ขอลิงก์หน่อย")
        # Should return direct URL from context
        print(f"Q: '(After Position) ขอลิงก์' -> A: {res['answer']}")
        self.assertEqual(res["route"], "context_followup")
        self.assertIn("http", res["answer"])
        self.assertIn("URL:", res["answer"])

    def test_position_ask_phone_recursive(self):
        print("\n[TEST] Position -> Ask Phone (Recursive)")
        # 1. Ask Position "ผส.บลตน." (Director, has name, maybe no phone in position record but has contact)
        self.chat_engine.process("ผส.บลตน.")
        
        # 2. Ask Phone
        res = self.chat_engine.process("ขอเบอร์")
        print(f"Q: '(After Position) ขอเบอร์' -> A: {res['answer']}")
        
        # Should be phone or explicitly "not found" (since we handle miss now)
        if res["route"] == "context_followup":
             self.assertIn("เบอร์", res["answer"])
             self.assertIn("074251450", res["answer"].replace("-", "")) # Normalize check
        else:
             self.fail(f"Expected Phone Found, got {res['route']}: {res['answer']}")

if __name__ == "__main__":
    unittest.main()
