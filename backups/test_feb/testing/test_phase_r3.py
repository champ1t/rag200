
import unittest
import time
import sys
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()

from src.rag.safety_guard import SafetyGuard
from src.rag.cache_manager import CacheManager

class TestPhaseR3(unittest.TestCase):
    
    def test_kill_switch_safety(self):
        # 1. Low Score
        hit_low = MagicMock()
        hit_low.score = 0.2
        hit_low.metadata = {"title": "Good Doc"}
        hit_low.text = "Some content"
        res = SafetyGuard.check_retrieval_safety([hit_low])
        self.assertFalse(res["safe"])
        self.assertIn("score too low", res["reason"])
        
        # 2. Boilerplate
        hit_bp = MagicMock()
        hit_bp.score = 0.8
        hit_bp.metadata = {"title": "Home"}
        hit_bp.text = "Menu..."
        res = SafetyGuard.check_retrieval_safety([hit_bp])
        self.assertFalse(res["safe"])
        self.assertIn("Boilerplate", res["reason"])
        
        # 3. Safe
        hit_safe = MagicMock()
        hit_safe.score = 0.8
        hit_safe.metadata = {"title": "Manual"}
        hit_safe.text = "A" * 300 # > 200 chars
        res = SafetyGuard.check_retrieval_safety([hit_safe])
        self.assertTrue(res["safe"])

    def test_cache_manager_l1(self):
        cm = CacheManager()
        hits = ["hit1", "hit2"]
        
        # Miss
        self.assertIsNone(cm.get_retrieval_cache("q1", "mode1"))
        
        # Set
        cm.set_retrieval_cache("q1", "mode1", hits)
        
        # Hit
        cached = cm.get_retrieval_cache("q1", "mode1")
        self.assertEqual(cached, hits)
        
        # Miss (Diff Query)
        self.assertIsNone(cm.get_retrieval_cache("q2", "mode1"))

    def test_cache_manager_l2_fingerprint(self):
        sem_mock = MagicMock()
        cm = CacheManager(sem_mock)
        
        # Compute Fingerprint
        h1 = MagicMock()
        h1.id = "doc1"
        h1.text = "abc"
        hits = [h1]
        
        fp = cm.compute_fingerprint(hits)
        
        # Check
        cm.get_answer_cache("q", "intent", fp)
        sem_mock.check.assert_called_with(
            "q", 
            intent="intent", 
            route="rag", 
            filter_meta={"fingerprint": fp}
        )

if __name__ == "__main__":
    unittest.main()
