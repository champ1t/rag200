import unittest
from unittest.mock import MagicMock, patch
import yaml
import sys
import os

# Adjust path to import src
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

class TestSafetyGuard(unittest.TestCase):
    def setUp(self):
        # Load real config to ensure structure is correct
        try:
            config = yaml.safe_load(open("configs/config.yaml"))
        except:
            config = {} # Fallback
            
        self.engine = ChatEngine(config)
        
        # Mock processed_cache
        self.engine.processed_cache = MagicMock()
        self.engine.processed_cache.normalize_for_matching.return_value = "query"
        self.engine.processed_cache.soft_normalize.return_value = "query"
        self.engine.processed_cache.find_best_article_match.return_value = None
        self.engine.processed_cache._link_index = {} 
        self.engine.processed_cache.is_known_url.return_value = True

        # Mock RAG/Vector to catch fall-through
        self.engine._perform_rag = MagicMock(return_value={
            "route": "rag_answer",
            "answer": "RAG Answer",
            "metadata": {}
        })
        self.engine._handle_article_route = MagicMock(return_value={
            "route": "article_link_only_exact",
            "answer": "Article Answer",
            "metadata": {"url": "http://10.192.133.33/smc/1"}
        })
        
        # Mock internal compatibility
        self.engine._is_article_compatible = MagicMock(return_value=True)

    def test_case_1_ambiguity_trigger(self):
        print("\n🧪 TEST CASE 1: Ambiguity Trigger (คำสั่ง huawei)")
        # Setup: No exact match
        self.engine.processed_cache.find_best_article_match.return_value = None
        
        # Mock finding vendor articles
        self.engine._find_vendor_articles = MagicMock(return_value=[
             {"title": "Huawei Config 1", "url": "url1"},
             {"title": "Huawei Config 2", "url": "url2"}
        ])

        res = self.engine.process("คำสั่ง huawei")
        
        print(f"Route: {res.get('route')}")
        self.assertEqual(res["route"], "pending_clarification")
        self.assertEqual(res["metadata"]["kind"], "vendor_command_selection")
        self.assertTrue(len(res["metadata"]["candidates"]) >= 2)

    def test_case_2_numeric_selection(self):
        print("\n🧪 TEST CASE 2: Numeric Selection (1)")
        # Setup pending state manually
        import time
        self.engine.pending_question = {
            "kind": "vendor_command_selection",
            "candidates": [{"title": "Huawei Config 1", "url": "http://10.192.133.33/smc/1"}],
            "created_at": time.time()
        }
        
        res = self.engine.process("1")
        
        print(f"Route: {res.get('route')}")
        self.engine._handle_article_route.assert_called_with(
            url="http://10.192.133.33/smc/1",
            query="Huawei Config 1", # Must pass title as query
            latencies=unittest.mock.ANY,
            start_time=unittest.mock.ANY,
            match_score=1.0,
            intent="DETERMINISTIC_MATCH",
            article_type="COMMAND",
            decision_reason=unittest.mock.ANY
        )
        self.assertEqual(res["route"], "article_link_only_exact")

    def test_case_3_specific_model_bypass(self):
        print("\n🧪 TEST CASE 3: Specific Model Bypass (Huawei NE8000)")
        # Setup: No exact match (so falls through Deterministic)
        # But Ambiguity Check should return False (Not Ambiguous)
        # So it should hit RAG/Vector Search (mocked)
        self.engine.processed_cache.find_best_article_match.return_value = None
        
        res = self.engine.process("Huawei NE8000")
        
        print(f"Route: {res.get('route')}")
        self.assertNotEqual(res.get("route"), "pending_clarification")
        self.assertEqual(res.get("route"), "rag_answer")
        self.engine._perform_rag.assert_called()

    def test_case_4_governance_blocking(self):
        print("\n🧪 TEST CASE 4: Governance Blocking (คำสั่ง cisco)")
        # Setup: Cisco is SMC_ONLY. No exact match.
        self.engine.processed_cache.find_best_article_match.return_value = None
        
        # Ensure _detect_vendor_scope returns correctly (it uses internal logic, 
        # but we need to ensure processed_cache has no cisco articles if implied)
        # self.engine.processed_cache._link_index is empty by default in mock.
        
        res = self.engine.process("คำสั่ง cisco")
        
        print(f"Route: {res.get('route')}")
        self.assertEqual(res["route"], "blocked_vendor_out_of_scope")

    def test_priority_exact_match_over_ambiguity(self):
        print("\n🧪 TEST PRIORITY: Exact Match > Ambiguity")
        # Input: "คำสั่ง Huawei" (Normally Ambiguous)
        # Setup: Force an EXACT MATCH in Deterministic Phase
        self.engine.processed_cache.find_best_article_match.return_value = {
            "match_type": "deterministic",
            "score": 1.0,
            "title": "Exact Huawei Command",
            "url": "http://url",
            "article_type": "COMMAND"
        }
        
        res = self.engine.process("คำสั่ง Huawei")
        
        print(f"Route: {res.get('route')}")
        # Should be article, NOT pending_clarification
        self.assertEqual(res["route"], "article_link_only_exact")

if __name__ == '__main__':
    unittest.main()
