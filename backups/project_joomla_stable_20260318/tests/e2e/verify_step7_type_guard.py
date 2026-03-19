import unittest
from unittest.mock import MagicMock
import yaml
import sys
import os

sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

class TestTypeGuard(unittest.TestCase):
    def setUp(self):
        try:
           config = yaml.safe_load(open("configs/config.yaml"))
        except:
           config = {}
        self.engine = ChatEngine(config)
        self.engine.processed_cache = MagicMock()
        self.engine.processed_cache.normalize_for_matching.return_value = "ncs"
        self.engine.processed_cache.soft_normalize.return_value = "ncs"
        self.engine.processed_cache.is_known_url.return_value = True
        
        # Mock Deterministic Match: Command NCS (COMMAND_REFERENCE)
        self.engine.processed_cache.find_best_article_match.return_value = {
            "match_type": "deterministic",
            "score": 1.0,
            "title": "Command NCS",
            "url": "http://smc/ncs",
            "article_type": "COMMAND_REFERENCE"
        }
        
        # Mock Intent: OVERVIEW
        self.engine._classify_intent = MagicMock(return_value="OVERVIEW")
        
        # Mock RAG Fallback
        self.engine._perform_rag = MagicMock(return_value={
            "route": "rag_answer",
            "answer": "Specific Overview Answer form Semantic Search",
            "latencies": {"rag": 0.1}
        })
        
        # Mock Article Route
        self.engine._handle_article_route = MagicMock(return_value={
            "route": "article_link_only_exact",
            "answer": "Link Only",
            "metadata": {}
        })

    def test_overview_rejects_command_ref(self):
        print("\n🧪 TEST: OVERVIEW intent vs COMMAND_REFERENCE article")
        # Setup specific intent override for this test if needed (already set in setUp)
        
        res = self.engine.process("ข้อจำกัดของ NCS")
        
        # Expect RAG Answer (Fallback), NOT Deterministic Article Route
        print(f"Route: {res.get('route')}")
        self.assertEqual(res["route"], "rag_answer")
        self.engine._perform_rag.assert_called()
        
    def test_command_accepts_command_ref(self):
        print("\n🧪 TEST: COMMAND intent vs COMMAND_REFERENCE article")
        # Change intent to COMMAND
        self.engine._classify_intent.return_value = "COMMAND"
        
        res = self.engine.process("Command NCS")
        
        # Expect Deterministic Match
        print(f"Route: {res.get('route')}")
        self.assertEqual(res["route"], "article_link_only_exact")
        
if __name__ == '__main__':
    unittest.main()
