import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

MOCK_CFG = {
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"show_context": False},
    "rag": {"use_cache": False, "router_model": "mock"},
    "retrieval": {"top_k": 3},
    "security": {"hardening_threshold": 0.8}
}

class TestIntentGovernance(unittest.TestCase):
    def setUp(self):
        import inspect
        import sys
        print(f"DEBUG: sys.path: {sys.path}")
        print(f"DEBUG: ChatEngine File: {inspect.getfile(ChatEngine)}")
        
        # Patch heavy dependencies to prevent actual loading

        self.patcher1 = patch('src.chat_engine.build_vectorstore', return_value=MagicMock())
        self.patcher2 = patch('src.chat_engine.load_records', return_value=[])
        self.patcher3 = patch('src.chat_engine.WebHandler', return_value=MagicMock())
        # We need to patch ProcessedCache to verify find_best_article_match
        self.patcher4 = patch('src.chat_engine.ProcessedCache', autospec=True) 
        
        self.mock_vs_init_rv = self.patcher1.start() 
        self.mock_records = self.patcher2.start()
        self.mock_web_cls = self.patcher3.start()
        self.MockProcessedCache = self.patcher4.start()
        
        # Setup Mock ProcessedCache instance
        self.mock_cache_instance = self.MockProcessedCache.return_value
        self.mock_cache_instance.aliases = {}
        # Default behavior: None
        self.mock_cache_instance.find_best_article_match.return_value = None
        self.mock_cache_instance.find_links_fuzzy.return_value = [] # Fix TypeError
        self.mock_cache_instance.normalize_for_matching.side_effect = lambda x: x.lower().strip()
        
        # Init Engine
        self.engine = ChatEngine(MOCK_CFG)
        
        # Ensure our mock cache is attached
        self.engine.processed_cache = self.mock_cache_instance
        
        # Mock VS
        self.engine.vs = MagicMock()
        self.engine.vs.query.return_value = []
        self.engine.vs.hybrid_query.return_value = []
        
        # Mock content processing to avoid failures
        self.engine.article_interpreter = MagicMock()
        self.engine.article_interpreter.interpret.return_value = "Mock Answer"
        
        # Mock fetch logic
        self.engine.web_handler.fetch_page_text.return_value = "Mock Content"
        
    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()

    def test_01_intent_classification(self):
        """Verify _classify_intent logic"""
        # Config
        self.assertEqual(self.engine._classify_intent("Huawei NE8000 config"), "CONFIG")
        self.assertEqual(self.engine._classify_intent("set command for cisc"), "CONFIG")
        self.assertEqual(self.engine._classify_intent("ตั้งค่า OLT"), "CONFIG")
        self.assertEqual(self.engine._classify_intent("BGP setup"), "CONFIG") # 'setup' is CONFIG keyword
        
        # Protocol
        self.assertEqual(self.engine._classify_intent("BGP routing"), "PROTOCOL") # 'routing' not in keywords? Wait.
        self.assertEqual(self.engine._classify_intent("OSPF network"), "PROTOCOL")
        
        # Overview
        self.assertEqual(self.engine._classify_intent("What is SRv6"), "OVERVIEW")
        self.assertEqual(self.engine._classify_intent("NE8000 overview"), "OVERVIEW")
        self.assertEqual(self.engine._classify_intent("คืออะไร"), "OVERVIEW")
        
        # Troubleshoot
        self.assertEqual(self.engine._classify_intent("interface error"), "TROUBLESHOOT")
        self.assertEqual(self.engine._classify_intent("แก้ปัญหา link down"), "TROUBLESHOOT")

    def test_02_out_of_scope_blocking(self):
        """Rule 6: Out-of-Scope queries MUST be blocked"""
        queries = [
            "Your opinion on Huawei vs Cisco",
            "Which is better NE8000 or ASR9K",
            "Why is ZTE bad",
            "Recommend best router"
        ]
        
        for q in queries:
            print(f"Testing Blocking for: '{q}'")
            res = self.engine.process(q)
            self.assertEqual(res.get("block_reason"), "OUT_OF_SCOPE_QUERY")
            self.assertEqual(res.get("route"), "blocked_scope")
            self.assertIn("Out of Scope", res.get("answer"))

    def test_03_ambiguity_blocking(self):
        """Rule: Ambiguous matches MUST block"""
        query = "Reset Config"
        
        # Mock Ambiguous Return
        self.mock_cache_instance.find_best_article_match.return_value = {
            "match_type": "ambiguous",
            "candidates": ["Reset Config C300", "Reset Config NE8000"],
            "score": 0.85
        }
        
        print(f"Testing Ambiguity for: '{query}'")
        res = self.engine.process(query)
        
        self.assertEqual(res.get("block_reason"), "AMBIGUOUS_QUERY")
        self.assertEqual(res.get("route"), "blocked_ambiguous")
        self.assertIn("คำถามกำกวม", res.get("answer"))
        self.assertIn("Reset Config C300", res.get("answer"))

    def test_04_intent_mismatch_blocking(self):
        """Rule: Intent Mismatch (Config vs Overview) MUST block"""
        # Engine will classify query as CONFIG
        query = "Huawei NE8000 Config" 
        
        # Mock Deterministic Hit but with OVERVIEW type title
        self.mock_cache_instance.find_best_article_match.return_value = {
            "match_type": "deterministic",
            "title": "Huawei NE8000 Overview",
            "url": "http://10.192.133.33/ne8000/overview",
            "score": 1.0,
            "text": "Overview of NE8000"
        }
        
        print(f"Testing Intent Mismatch for: '{query}'")
        res = self.engine.process(query)
        
        # Check classification match
        # query -> "CONFIG"
        # title -> "OVERVIEW"
        # Should Block
        
        self.assertEqual(res.get("block_reason"), "INTENT_MISMATCH")
        self.assertEqual(res.get("route"), "blocked_intent")
        self.assertIn("เนื้อหาไม่ตรงตามจุดประสงค์", res.get("answer"))

    def test_05_valid_match_success(self):
        """Rule: Valid Match MUST succeed"""
        query = "Huawei NE8000 Config" # Intent: CONFIG
        
        # Mock Deterministic Hit with Config type
        self.mock_cache_instance.find_best_article_match.return_value = {
            "match_type": "deterministic",
            "title": "Huawei NE8000 Configuration Guide", # Intent: CONFIG
            "url": "http://10.192.133.33/ne8000/config",
            "score": 1.0,
            "text": "Config Guide"
        }
        
        print(f"Testing Success for: '{query}'")
        
        # Debug Checks
        print(f"DEBUG: Cache Type: {type(self.engine.processed_cache)}")
        print(f"DEBUG: Mock Value: {self.engine.processed_cache.find_best_article_match('q')}")
        print(f"DEBUG: Threshold: {self.engine.hardening_threshold}")
        
        res = self.engine.process(query)
        print(f"DEBUG: Result Keys: {list(res.keys())}")
        print(f"DEBUG: Route: {res.get('route')}")
        
        self.assertEqual(res.get("intent"), "DETERMINISTIC_MATCH")
        self.assertIn("Mock Answer", res.get("answer"))

if __name__ == "__main__":
    unittest.main()
