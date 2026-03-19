import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to find src
sys.path.append(os.getcwd())
try:
    from src.core.chat_engine import ChatEngine
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), "src"))
    from src.core.chat_engine import ChatEngine

class TestStep16(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "hardening": {"enabled": True}, 
            "retrieval": {"top_k": 7},
            "llm": {"model": "gpt-4o"},
            "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
        }
        self.engine = ChatEngine(self.mock_config)
        self.engine.processed_cache = MagicMock()
        self.engine.processed_cache._loaded = True
        
    def test_ranking_logic(self):
        print("\n[TEST] 16.1 Ranking Logic & Categories")
        
        # Mock Index
        mock_index = {
            "t1": {"text": "Huawei OLT Guide", "href": "u1"},
            "t2": {"text": "คำสั่งพื้นฐาน Huawei NE8000", "href": "u2"},
            "t3": {"text": "Config VAS by Huawei", "href": "u3"},
            "t4": {"text": "Huawei 577K Checking", "href": "u4"},
            "t5": {"text": "Huawei System Overview", "href": "u5"},
            "t6": {"text": "General Huawei Info", "href": "u6"}
        }
        self.engine.processed_cache._normalized_title_index = mock_index
        
        # Call _find_vendor_articles
        # Expected Scores:
        # t2: "คำสั่งพื้นฐาน" -> +5 => Score 5
        # t5: "Overview" -> +3 => Score 3
        # t3: "Config" -> +2 => Score 2
        # t4: "Checking" -> +1 => Score 1
        # t1: "OLT" -> 0 => Score 0
        # t6: "General" -> 0 => Score 0
        
        results = self.engine._find_vendor_articles("Huawei")
        
        # Verify Order
        titles = [r['title'] for r in results]
        print(f"Ranked Titles: {titles}")
        
        expected_order = [
            "คำสั่งพื้นฐาน Huawei NE8000", # 5
            "Huawei System Overview",      # 3
            "Config VAS by Huawei",        # 2
            "Huawei 577K Checking",        # 1
            "General Huawei Info",         # 0 (Alphabetical G < H)
            "Huawei OLT Guide"             # 0
        ]
        
        self.assertEqual(titles[0], expected_order[0])
        self.assertEqual(titles[1], expected_order[1])
        self.assertEqual(titles[2], expected_order[2])
        self.assertEqual(titles[3], expected_order[3])
        
        # Verify Categories
        cat_map = {r['title']: r['category'] for r in results}
        print(f"Categories: {cat_map}")
        
        self.assertEqual(cat_map["คำสั่งพื้นฐาน Huawei NE8000"], "คำสั่งพื้นฐาน")
        self.assertEqual(cat_map["Huawei OLT Guide"], "OLT / ONT")
        self.assertEqual(cat_map["Config VAS by Huawei"], "Configuration")
        self.assertEqual(cat_map["Huawei System Overview"], "ทั่วไป") # Overview not in category map rules, falls to general?
        # Rule: "If title contains... 'config' -> Configuration... else -> ทั่วไป"
        # Wait, Step 4 said: "คำสั่งพื้นฐาน", "olt/ont", "config". Else "ทั่วไป".
        # So "Overview" should be "ทั่วไป".
        
    def test_grouping_display(self):
        print("\n[TEST] 16.2 Grouping Display in Process")
        
        # Mock Ambiguity to trigger BROAD_VENDOR_COMMAND
        with patch('src.query_analysis.ambiguity_detector.check_ambiguity') as mock_check:
            mock_check.return_value = {"is_ambiguous": True, "reason": "BROAD_VENDOR_COMMAND"}
            with patch('src.query_analysis.ambiguity_detector.AmbiguityDetector.extract_vendor') as mock_extract:
                 mock_extract.return_value = "Huawei"
                 
                 # Ensure _find_vendor_articles returns data (mocking it or using the one from previous test if using same instance?)
                 # We can mock _find_vendor_articles to return controlled list
                 self.engine._find_vendor_articles = MagicMock(return_value=[
                     {'title': 'T1', 'category': 'คำสั่งพื้นฐาน', 'smc_priority_score': 5, 'url': 'u1'},
                     {'title': 'T2', 'category': 'Configuration', 'smc_priority_score': 2, 'url': 'u2'},
                     {'title': 'T3', 'category': 'คำสั่งพื้นฐาน', 'smc_priority_score': 5, 'url': 'u3'}
                 ])
                 
                 res = self.engine.process("คำสั่ง huawei")
                 
                 ans = res['answer']
                 print(f"Answer:\n{ans}")
                 
                 self.assertIn("พบเอกสารที่เกี่ยวข้องในระบบ SMC ดังนี้", ans)
                 self.assertIn("\n[คำสั่งพื้นฐาน]\n", ans)
                 self.assertIn("• T1", ans)
                 self.assertIn("• T3", ans)
                 self.assertIn("\n[Configuration]\n", ans)
                 self.assertIn("• T2", ans)

if __name__ == "__main__":
    unittest.main()
