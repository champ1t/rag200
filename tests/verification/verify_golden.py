
import unittest
import json
import os
from src.rag.article_cleaner import clean_article_content, deduplicate_paragraphs

class TestGoldenCases(unittest.TestCase):
    def setUp(self):
        with open("data/golden_cases.json", "r") as f:
            self.cases = json.load(f)
            
    def test_all_cases(self):
        print("\n=== Golden Regression Tests ===")
        for key, case in self.cases.items():
            print(f"Checking {key}: {case['description']}")
            
            # 1. Clean Garbage
            cleaned = clean_article_content(case['input'])
            
            # 2. Dedup
            deduped = deduplicate_paragraphs(cleaned)
            
            # Checks
            # Forbidden
            for bad in case["forbidden"]:
                if bad in deduped:
                    print(f"FAILED: Found forbidden '{bad}' in {key}")
                self.assertNotIn(bad, deduped, f"[{key}] Found forbidden term: {bad}")
                
            # Required
            for req in case["required"]:
                 if req not in deduped:
                    print(f"FAILED: Missing required '{req}' in {key}")
                 self.assertIn(req, deduped, f"[{key}] Missing required term: {req}")
                 
            # Max Repeated Blocks
            if "max_repeated_blocks" in case:
                # Naive check: Count exact line repeats? 
                # Dedup function handles blocks.
                # Let's count if any block appears > 1 time
                blocks = deduped.split('\n\n')
                from collections import Counter
                ctr = Counter([b.strip() for b in blocks if b.strip()])
                repeats = sum(1 for k, v in ctr.items() if v > 1)
                self.assertEqual(repeats, case["max_repeated_blocks"], f"[{key}] Found {repeats} repeated blocks, expected {case['max_repeated_blocks']}")

            print(f"PASS: {key}")

if __name__ == '__main__':
    unittest.main()
