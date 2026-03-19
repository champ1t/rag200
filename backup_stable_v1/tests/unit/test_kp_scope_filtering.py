
import sys
import os
import unittest
sys.path.append(os.getcwd())
from src.chat_engine import ChatEngine

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

class TestKPScopeFiltering(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        
    def test_dns_nt1_filtering(self):
        print("\n--- Test: DNS NT1 Scope Filtering ---")
        # "DNS NT1" should return facts that have scope="NT1"
        res = self.engine.process("DNS NT1")
        self.assertIn(res["route"], ["knowledge_pack_resolved", "knowledge_pack"])
        
        hits = res["hits"]
        self.assertTrue(len(hits) > 0)
        
        # Verify scope metadata (if available in memory)
        # Note: In production `hits` contains dicts.
        for fact in hits:
            # We expect either scope="NT1" OR if fallback happened, message in answer.
            # But "DNS NT1" definitely has facts, so no fallback expected.
            self.assertEqual(fact.get("scope"), "NT1", f"Fact {fact.get('key')} has wrong scope")
            
    def test_dns_region_filtering(self):
        print("\n--- Test: DNS Region Scope Filtering ---")
        # "DNS ภูมิภาค" should return scope="Region"
        res = self.engine.process("DNS ภูมิภาค")
        hits = res["hits"]
        self.assertTrue(len(hits) > 0)
        for fact in hits:
             self.assertEqual(fact.get("scope"), "Region")

    def test_fallback_warning(self):
        print("\n--- Test: Fallback Warning (Empty Scope) ---")
        # Use a scope that likely has no DNS data but is valid: ISP (maybe default has some, let's see)
        # Or force a mismatch?
        # If I type "DNS ISP", and no ISP DNS exists, it should show All + Warning.
        res = self.engine.process("DNS ISP")
        
        # Check if fallback triggered
        if "ไม่พบข้อมูลในขอบเขต ISP" in res["answer"]:
            print("Fallback triggered successfully.")
            # Then hits should be mixed or all
        else:
            # If no fallback, verify they truly are ISP scope
            hits = res.get("hits", [])
            for fact in hits:
                self.assertEqual(fact.get("scope"), "ISP")

if __name__ == "__main__":
    unittest.main()
