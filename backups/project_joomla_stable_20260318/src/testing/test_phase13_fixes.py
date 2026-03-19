import unittest
import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.chat_engine import ChatEngine

# Mock Config
CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestPhase13Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SETUP] Initializing ChatEngine for Phase 13 Tests...")
        cls.engine = ChatEngine(CFG)
        
    def setUp(self):
        self.engine.last_context = None
        
    def test_followup_entity_override(self):
        """Test 'ขอเบอร์ผจ' after 'ผส' routes to position_lookup, not context_followup"""
        # Step 1: Lookup ผส (Director)
        res1 = self.engine.process("ใครคือผส.บลตน.")
        self.assertEqual(res1["route"], "position_lookup")
        self.assertIn("สมบูรณ์", res1["answer"])
        
        # Step 2: Request phone for ผจ (Manager) - should NOT use last_context
        res2 = self.engine.process("ขอเบอร์ผจ")
        
        # Must route to position_lookup (or contact_name), NOT context_followup
        self.assertIn(res2["route"], ["position_lookup", "contact_name"])
        
        # Must return ผจ data (ปรัชญา), NOT ผส data (สมบูรณ์)
        self.assertIn("ปรัชญา", res2["answer"])
        self.assertNotIn("สมบูรณ์", res2["answer"])
        
        print(f"\n[PASS] Follow-up Override: route={res2['route']}")
        
    def test_clarify_timing_consistency(self):
        """Test clarify route has consistent timing and no generator/evaluator"""
        # Mock retrieval to ensure heuristic clarify triggers
        from collections import namedtuple
        Doc = namedtuple("Doc", ["text", "score", "metadata"])
        
        if hasattr(self.engine.vs, "hybrid_query"):
            original_search = self.engine.vs.hybrid_query
            self.engine.vs.hybrid_query = lambda q, top_k, alpha=0.5, where=None: [Doc("irrelevant", 0.5, {})]
        else:
            original_search = self.engine.vs.query
            self.engine.vs.query = lambda q, top_k, where=None: [Doc("irrelevant", 0.5, {})]
        
        try:
            t0 = time.time()
            res = self.engine.process("ปัญหา internet ใช้งานไม่ได้")
            duration = (time.time() - t0) * 1000
            
            # Check route
            self.assertEqual(res["route"], "rag_clarify")
            
            # Check timing fields exist
            self.assertIn("total", res["latencies"])
            self.assertIn("llm", res["latencies"])
            self.assertIn("clarify", res["latencies"])
            
            # Heuristic clarify should have llm=0 (no LLM calls)
            self.assertEqual(res["latencies"]["llm"], 0.0)
            self.assertEqual(res["latencies"]["clarify"], 0.0)
            
            # Total should be low (< 1s)
            self.assertLess(res["latencies"]["total"], 1000.0)
            
            print(f"\n[PASS] Clarify Timing: total={res['latencies']['total']:.2f}ms, llm={res['latencies']['llm']:.2f}ms")
            
        finally:
            if hasattr(self.engine.vs, "hybrid_query"):
                self.engine.vs.hybrid_query = original_search
            else:
                self.engine.vs.query = original_search
    
    def test_timing_fields_present(self):
        """Test all timing fields are initialized"""
        res = self.engine.process("hi")
        
        required_fields = ["routing", "embed", "vector_search", "bm25", "fusion",
                          "controller", "retrieval_opt", "generator", "evaluator",
                          "clarify", "total", "llm"]
        
        for field in required_fields:
            self.assertIn(field, res["latencies"], f"Missing timing field: {field}")
        
        print(f"\n[PASS] All timing fields present: {list(res['latencies'].keys())}")

if __name__ == "__main__":
    unittest.main()
