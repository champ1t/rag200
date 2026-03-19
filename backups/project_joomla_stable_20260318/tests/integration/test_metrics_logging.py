
import unittest
import sys
import os
import json
import time
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.utils.metrics import MetricsTracker

# Mock config
MOCK_CONFIG = {
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"show_context": False},
    "rag": {"use_cache": False},
    "security": {"hardening_threshold": 0.8},
    "retrieval": {"top_k": 3}
}

class TestMetricsLogging(unittest.TestCase):
    def setUp(self):
        # Setup clean metrics tracker
        self.log_dir = "logs_test"
        if os.path.exists(self.log_dir):
            import shutil
            shutil.rmtree(self.log_dir)
        os.makedirs(self.log_dir)
        
        self.tracker = MetricsTracker(log_dir=self.log_dir)
        
    def tearDown(self):
        # Cleanup
        import shutil
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)

    def test_log_writing_and_stats(self):
        # 1. Log a BLOCK
        self.tracker.log("query1", "intent1", "BLOCK", route="blocked_scope")
        
        # 2. Log a MISSING
        self.tracker.log("query2", "intent2", "MISSING", route="rag_missing_corpus")
        
        # 3. Log an ARTICLE_OK
        self.tracker.log("query3", "intent3", "ARTICLE_OK", route="article_answer")
        
        # Verify Stats File
        with open(os.path.join(self.log_dir, "dashboard_stats.json"), "r") as f:
            stats = json.load(f)
            
        self.assertEqual(stats["total_queries"], 3)
        self.assertEqual(stats["blocked_queries"], 1)
        self.assertEqual(stats["missing_article_queries"], 1)
        self.assertEqual(stats["article_served_queries"], 1)
        self.assertEqual(stats["cross_vendor_block_count"], 1) # blocked_scope -> cross_vendor count
        
        # Verify Transaction Log
        with open(os.path.join(self.log_dir, "query_metrics.jsonl"), "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)
            entry1 = json.loads(lines[0])
            self.assertEqual(entry1["query"], "query1")
            self.assertEqual(entry1["result"], "BLOCK")

    @patch("src.chat_engine.ChatEngine._check_out_of_scope")
    def test_integration_block(self, mock_check):
        # Test if ChatEngine actually calls metrics
        # We need to mock _check_out_of_scope to return True to trigger a block
        mock_check.return_value = True
        
        engine = ChatEngine(MOCK_CONFIG)
        engine.metrics = self.tracker # Inject our test tracker
        
        # Run process
        engine.process("bad query")
        
        # Verify metrics updated
        with open(os.path.join(self.log_dir, "dashboard_stats.json"), "r") as f:
            stats = json.load(f)
        
        self.assertEqual(stats["total_queries"], 1)
        self.assertEqual(stats["blocked_queries"], 1)

if __name__ == "__main__":
    unittest.main()
