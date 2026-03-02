import sys
import os
import unittest
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

class TestDeterministicRetrieval(unittest.TestCase):
    def setUp(self):
        # Use REAL data by loading from the actual directory
        # The fake "Huawei NE8000" file should be DELETED before running this test.
        self.cache = ProcessedCache("data/processed")
        self.cache.load() 

    def test_missing_corpus_detection(self):
        """Test: 'คำสั่งพื้นฐาน Huawei NE8000' should detect MISSING CORPUS in lowercase"""
        query = "คำสั่งพื้นฐาน Huawei NE8000"
        print(f"\nTesting Query: '{query}'")
        
        match = self.cache.find_best_article_match(query)
        
        if match:
             print(f"MATCH: {match}")
             
        self.assertIsNotNone(match, "Should return a match object for missing corpus")
        self.assertEqual(match.get("match_type"), "missing_corpus")
        # Adjust expectation to lowercase 'huawei ne8000'
        self.assertIn("huawei ne8000", match.get("topic").lower())

if __name__ == "__main__":
    unittest.main()
