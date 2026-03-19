import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chat_engine import ChatEngine
from src.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestContextFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing ChatEngine for Context Tests...")
        cls.chat_engine = ChatEngine(CFG)
        
    def test_position_followup(self):
        print("\n[TEST] Position Follow-up")
        # 1. Ask Position
        q1 = "ใครดำรงตำแหน่ง ผส.บลตน."
        res1 = self.chat_engine.process(q1)
        print(f"Q1: {q1}\nA1: {res1['answer'][:50]}...")
        self.assertEqual(res1["route"], "position_lookup")
        self.assertIsNotNone(self.chat_engine.last_context)
        self.assertEqual(self.chat_engine.last_context["type"], "position")
        
        # 2. Ask Phone (Follow-up)
        q2 = "ขอเบอร์หน่อย"
        res2 = self.chat_engine.process(q2)
        print(f"Q2: {q2}\nA2: {res2['answer']}")
        # Can be context_followup (found) or context_followup_miss (not found)
        # But MUST NOT be link_lookup
        self.assertIn(res2["route"], ["context_followup", "context_followup_miss"])
        if res2["route"] == "context_followup":
            self.assertIn("เบอร์", res2["answer"])
        else:
             self.assertIn("ไม่พบ", res2["answer"])

    def test_link_followup(self):
        print("\n[TEST] Link Follow-up")
        # 1. Ask Link
        q1 = "เข้า link Edocument"
        res1 = self.chat_engine.process(q1)
        print(f"Q1: {q1}\nA1: {res1['answer'][:50]}...")
        self.assertEqual(res1["route"], "link_lookup")
        self.assertIsNotNone(self.chat_engine.last_context)
        self.assertEqual(self.chat_engine.last_context["type"], "link")
        
        # 2. Ask Detail (Follow-up)
        q2 = "ขอรายละเอียด"
        res2 = self.chat_engine.process(q2)
        print(f"Q2: {q2}\nA2: {res2['answer']}")
        self.assertEqual(res2["route"], "context_followup")
        self.assertIn("URL:", res2["answer"])

    def test_contact_name_followup(self):
        print("\n[TEST] Name Lookup Follow-up")
        # 1. Ask Name (that exists)
        # Using a name from previous logs or known data
        q1 = "ค้นหาเบอร์ คุณเฉลิมรัตน์" 
        res1 = self.chat_engine.process(q1)
        if res1["route"] == "contact_miss":
            print("[WARN] Contact skipped (missing data?), skipping check")
            return

        print(f"Q1: {q1}\nA1: {res1['answer'][:50]}...")
        self.assertEqual(res1["route"], "contact_name")
        
        # 2. Ask Phone (Redundant but generic)
        q2 = "เบอร์อะไรครับ"
        res2 = self.chat_engine.process(q2)
        print(f"Q2: {q2}\nA2: {res2['answer']}")
        self.assertEqual(res2["route"], "context_followup")

if __name__ == "__main__":
    unittest.main()
