
import unittest
import sys
from unittest.mock import MagicMock

# Mock dependencies before import
sys.modules["requests"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()

from src.rag.retrieval_strategy import StrategyFactory
from src.rag.retrieval_optimizer import RetrievalOptimizer
from src.rag.evaluator import RAGEvaluator

class TestPhaseR1(unittest.TestCase):
    
    def test_strategy_factory(self):
        # 1. Fact -> Low Alpha (Keyword)
        s1 = StrategyFactory.get_strategy("HOWTO_PROCEDURE")
        self.assertEqual(s1.alpha, 0.3)
        self.assertEqual(s1.mode, "KEYWORD_HEAVY")
        
        # 2. Concept -> High Alpha (Vector)
        s2 = StrategyFactory.get_strategy("EXPLAIN")
        self.assertEqual(s2.alpha, 0.8)
        self.assertEqual(s2.mode, "VECTOR_HEAVY")
        
        # 3. Default -> Balanced
        s3 = StrategyFactory.get_strategy("GENERAL_QA")
        self.assertEqual(s3.alpha, 0.5)

    def test_optimizer_re_rank(self):
        opt = RetrievalOptimizer({})
        
        # Mock Results
        # R1: Generic Title ("Home"), Score 0.6
        r1 = MagicMock()
        r1.score = 0.6
        r1.metadata = {"title": "Home", "url": "http://home"}
        r1.text = "Generic content"
        
        # R2: Acronym Match ("SBC"), Score 0.4
        r2 = MagicMock()
        r2.score = 0.4
        r2.metadata = {"title": "SBC Config", "url": "http://sbc"}
        r2.text = "SBC configuration guide"
        
        results = [r1, r2]
        query = "sbc"
        
        ranked = opt.re_rank(results, query)
        
        # Expect R2 to be boosted above R1
        self.assertEqual(ranked[0].metadata["title"], "SBC Config")
        self.assertGreater(ranked[0].score, ranked[1].score)
        print(f"R1 Score: {ranked[1].score} (Penalized), R2 Score: {ranked[0].score} (Boosted)")

    def test_coverage_check(self):
        evaluator = RAGEvaluator({})
        
        # Case 1: Low Score -> MISS
        r_low = MagicMock()
        r_low.score = 0.2
        res = evaluator.check_coverage([r_low])
        self.assertEqual(res["status"], "MISS")
        
        # Case 2: Single Source -> LOW_CONFIDENCE if score < 0.75
        r_mid = MagicMock()
        r_mid.score = 0.5
        r_mid.metadata = {"url": "http://doc1"}
        r_mid2 = MagicMock()
        r_mid2.score = 0.6
        r_mid2.metadata = {"url": "http://doc1"} # Same source
        
        res = evaluator.check_coverage([r_mid, r_mid2])
        self.assertEqual(res["status"], "LOW_CONFIDENCE")
        
        # Case 3: Pass
        r_high = MagicMock()
        r_high.score = 0.8
        r_high.metadata = {"url": "http://doc1"}
        res = evaluator.check_coverage([r_high])
        self.assertEqual(res["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
