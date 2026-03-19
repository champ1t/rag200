
import sys
import os
import unittest
import time
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

# Mock Config
CONFIG = {
    "model": "llama3.2:3b",
    "base_url": "http://localhost:11434",
    "use_cache": False,
    "retrieval": {"top_k": 3, "score_threshold": 0.3},
    "llm": {"model": "llama3.2:3b", "base_url": "http://localhost:11434", "temperature": 0.0},
    "chat": {"save_log": False}, 
    "knowledge_pack": {"enabled": True}, 
    "cache": {"enabled": False}
}

class TestKPClarifyLifecycle(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        
    def test_interruption_by_new_query(self):
        print("\n--- Test: KP Clarification Interruption ---")
        # 1. Start Clarification
        self.engine.process("DNS")
        self.assertIsNotNone(self.engine.pending_kp_clarify)
        
        # 2. Interrupt with new query
        q_new = "ข่าวสาร vlan planning"
        res = self.engine.process(q_new)
        
        # Should NOT be a re-ask
        self.assertNotEqual(res["route"], "knowledge_pack_clarify_reask")
        # Should have cleared state
        self.assertIsNone(self.engine.pending_kp_clarify)
        # Should have routed to something else (e.g. rag_no_docs or article if implemented)
        print(f"Interrupted Route: {res.get('route')}")
        
    def test_ttl_expiry(self):
        print("\n--- Test: KP Clarification TTL ---")
        # 1. Start
        self.engine.process("DNS")
        
        # 2. Manipulate TS to simulate expiry (>60s)
        self.engine.pending_kp_clarify["created_ts"] = time.time() - 70
        
        # 3. Next input (even if ambiguous) should be treated as new query
        res = self.engine.process("something")
        
        # Should clear state
        self.assertIsNone(self.engine.pending_kp_clarify)
        print(f"Expired Route: {res.get('route')}")
        
    def test_max_turns_expiry(self):
        print("\n--- Test: KP Max Turns ---")
        self.engine.process("DNS")
        
        # 1. Invalid Reply 1 (Turn 0 -> 1)
        res1 = self.engine.process("xyz")
        self.assertEqual(res1["route"], "knowledge_pack_clarify_reask")
        self.assertEqual(self.engine.pending_kp_clarify["turns"], 1)
        
        # 2. Invalid Reply 2 (Turn 1 -> Exceed)
        res2 = self.engine.process("abc")
        # Should NOT re-ask again, should fall through
        self.assertNotEqual(res2["route"], "knowledge_pack_clarify_reask")
        self.assertIsNone(self.engine.pending_kp_clarify)
        print(f"Max Turns Route: {res2.get('route')}")

if __name__ == "__main__":
    unittest.main()
