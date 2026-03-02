import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

class TestDeterministicRetrieval(unittest.TestCase):
    def setUp(self):
        self.cache = ProcessedCache("data/processed")
        # Mock load to populate index manually
        self.cache._loaded = True
        self.cache._link_index = {
            # False Positive Scenario
            # Title: "How to checking Huawei 577K" (Tokens: checking, huawei, 577k)
            # Query: "คำสั่งพื้นฐาน Huawei NE8000" (Tokens: huawei, ne8000) -> Overlap: {huawei} = 0.5
            "how to checking huawei 577k": [{"text": "How to checking Huawei 577K", "href": "url_fail"}]
        }

    def test_false_positive_rejection(self):
        """Test: 'คำสั่งพื้นฐาน Huawei NE8000' should NOT match 'Huawei 577K' (Score 0.5)"""
        # We want this to return None because 0.5 on a 2-token query is too weak (just brand match)
        query = "คำสั่งพื้นฐาน Huawei NE8000"
        print(f"\nTesting Query: '{query}'")
        
        match = self.cache.find_best_article_match(query)
        
        if match:
            print(f"MATCHED: {match['title']} (Score: {match['score']})")
            if match['score'] <= 0.5:
                 print("Result: FAIL (Matched weak score)")
            else:
                 print("Result: PASS (Matched strong score?? unexpected for this test)")
        else:
            print("NO MATCH FOUND (Correctly Rejected)")
            
        # We assert that it *should NOT* match (None)
        self.assertIsNone(match, "Should NOT match Huawei 577K with low confidence")

if __name__ == "__main__":
    unittest.main()
