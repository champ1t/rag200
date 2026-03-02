
import sys
import os
import unittest
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

# Mock Config
CONFIG = {
    "model": "llama3.2:3b",
    "base_url": "http://localhost:11434",
    "use_cache": False,
    "retrieval": {"top_k": 3, "score_threshold": 0.3},
    "llm": {"model": "llama3.2:3b", "base_url": "http://localhost:11434", "temperature": 0.2},
    "chat": {"save_log": False}, 
    "knowledge_pack": {"enabled": True},
    "cache": {"enabled": False}
}

class TestKPClarifyResolver(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        
    def test_a_dns_nt1_resolution(self):
        print("\n--- Test A: DNS -> NT1 Resolution ---")
        # 1. Ask Broad
        res1 = self.engine.process("DNS")
        self.assertEqual(res1["route"], "knowledge_pack_clarify")
        self.assertIsNotNone(self.engine.pending_kp_clarify)
        
        # 2. Reply Specific
        res2 = self.engine.process("NT1")
        self.assertIn("route", res2)
        # It should be resolved
        self.assertIn(res2["route"], ["knowledge_pack_resolved", "knowledge_pack"])
        self.assertIn("10.192.133.33", res2["answer"]) # NT1 DNS IP
        self.assertIsNone(self.engine.pending_kp_clarify)
        
    def test_b_dns_url_only_persistence(self):
        print("\n--- Test B: DNS (URL Only) -> NT1 Persistence ---")
        # 1. Ask Broad with Mode
        res1 = self.engine.process("DNS ขอลิงก์")
        self.assertEqual(res1["route"], "knowledge_pack_clarify")
        # Check pending mode
        self.assertEqual(self.engine.pending_kp_clarify["pending_answer_mode"], "URL_ONLY")
        
        # 2. Reply Specific
        res2 = self.engine.process("NT1")
        self.assertIn(res2["route"], ["knowledge_pack_resolved", "knowledge_pack"])
        # Should be URL ONLY
        self.assertIn("http", res2["answer"]) 
        # Should NOT contain multiple repeats (Dedup check logic could be added here)
        
    def test_c_dns_all_resolution(self):
        print("\n--- Test C: DNS -> All Resolution ---")
        # 1. Ask Broad
        self.engine.process("DNS")
        
        # 2. Reply "ทั้งหมด"
        res2 = self.engine.process("ทั้งหมด")
        self.assertIn(res2["route"], ["knowledge_pack_resolved", "knowledge_pack"])
        # Should contain multiple items
        self.assertTrue(len(res2["hits"]) > 3)
        self.assertIsNone(self.engine.pending_kp_clarify)
        
    def test_d_invalid_reply(self):
        print("\n--- Test D: Invalid Reply Re-ask ---")
        self.engine.process("DNS")
        
        # 2. Reply Invalid
        # "nt3" now matches "nt" alias, so use something else
        res2 = self.engine.process("xyz") 
        
        self.assertEqual(res2["route"], "knowledge_pack_clarify_reask")
        self.assertIn("พิมพ์เลือกขอบเขต", res2["answer"])
        self.assertIsNotNone(self.engine.pending_kp_clarify) # Should persist

if __name__ == "__main__":
    unittest.main()
