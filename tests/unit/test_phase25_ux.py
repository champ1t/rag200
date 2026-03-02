
import unittest
from src.core.chat_engine import ChatEngine

def get_config():
    return {
        "model": "llama3.2:3b",
        "base_url": "http://localhost:11434",
        "use_cache": False,
        # Mock retrieval config
        "retrieval": {
            "top_k": 5,
            "score_threshold": 0.3
        },
        "llm": {
             "model": "llama3.2:3b",
             "base_url": "http://localhost:11434",
             "temperature": 0.2
        },
        "cache": {
             "enabled": False
        },
        "knowledge_pack": {
             "enabled": True
        }
    }

import inspect
import src.chat_engine

class TestPhase25UX(unittest.TestCase):
    def setUp(self):
        print(f"ChatEngine File: {src.chat_engine.__file__}")
        self.cfg = get_config()
        self.engine = ChatEngine(self.cfg)
        self.engine.warmup()
        # Verify source code
        print("[DEBUG] Inspecting ChatEngine.process:")
        print(inspect.getsource(self.engine.process)[:300]) # First 300 chars
        print(f"KP Facts Loaded: {len(self.engine.kp_manager.facts)}")
        print(f"KP Dir: {self.engine.kp_manager.pack_dir}")
        self.assertTrue(len(self.engine.kp_manager.facts) > 0, "Knowledge Pack facts not loaded!")
        
    def test_clarification_options(self):
        print("\n--- Test Clarification Options ---")
        q = "DNS"
        # Debugging routing
        # Check intent flags
        print(f"Is Procedural? {any(k in q.lower() for k in ['ขั้นตอน', 'วิธี'])}")
        
        res = self.engine.process(q)
        print(f"Q: {q}")
        print(f"A: {res['answer']}")
        print(f"Route: {res['route']}")
        
        self.assertEqual(res["route"], "knowledge_pack_clarify")
        self.assertIn("กรุณาเลือกขอบเขต", res["answer"])
        self.assertIn("[NT1]", res["answer"]) # Presumes options logic identified NT1
        
        # Test Follow-up
        print("\n--- Test Follow-up Scope ---")
        q2 = "NT1"
        res2 = self.engine.process(q2)
        print(f"Q: {q2}")
        print(f"A: {res2['answer']}")
        
        self.assertEqual(res2["route"], "knowledge_pack")
        self.assertTrue(len(res2["hits"]) > 0)
        
    def test_answer_mode_ip_only(self):
        print("\n--- Test Answer Mode: IP ONLY ---")
        q = "Bras IP ขอแค่ ip"
        res = self.engine.process(q)
        print(f"Q: {q}")
        print(f"A: {res['answer']}")
        
        self.assertEqual(res["route"], "knowledge_pack")
        self.assertIn("IP Addresses", res["answer"])
        # Should not have typical verbose text
        self.assertNotIn("แหล่งข้อมูลอ้างอิง", res["answer"]) # If mode filters plain answer

if __name__ == '__main__':
    unittest.main()
