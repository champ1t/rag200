
import unittest
from src.rag.article_cleaner import detect_and_summarize_tables, extract_topic_anchored_facts, _is_valid_fact

class TestArticleCleanerOpt(unittest.TestCase):
    def test_table_summarization(self):
        # Create a mock table of 10 rows
        lines = [
            "Header Col1 | Col2",
            "1 | Data1",
            "2 | Data2",
            "3 | Data3",
            "4 | Data4",
            "5 | Data5",
            "6 | Data6",
            "7 | Data7",
            "8 | Data8",
            "Footer"
        ]
        
        summary = detect_and_summarize_tables(lines)
        
        # Check logic: Should keep Header, rows 1-3, and a summary line.
        # Header (0), Row1 (1), Row2 (2), Row3 (3), Summary (4)
        print(f"Summary: {summary}")
        
        self.assertIn("Header Col1 | Col2", summary)
        self.assertIn("3 | Data3", summary)
        self.assertNotIn("6 | Data6", summary) # Should be cut
        self.assertTrue(any("และอีก" in l for l in summary))
        
    def test_fact_ranking(self):
        content = """
        1. Important Fact about Asset 123
        2. Irrelevant Menu Link (http://test.com)
        3. Another Asset Info 456
        """
        
        # Query specifically for "Asset"
        facts = extract_topic_anchored_facts(content, "Asset")
        
        # "Important Fact" and "Another Asset Info" should differ in score if keywords match? 
        # "Menu Link" should be filtered out by _is_valid_fact strict filter or low score.
        
        self.assertTrue(any("Important Fact" in f for f in facts))
        self.assertTrue(any("Another Asset" in f for f in facts))
        self.assertFalse(any("Menu Link" in f for f in facts)) # Should be dropped
        
    def test_deduplication(self):
        content = """
        1. Duplicate Fact.
        2. Duplicate Fact!
        3. Unique Fact.
        """
        facts = extract_topic_anchored_facts(content, "Fact")
        print(f"Deduped Facts: {facts}")
        
        self.assertEqual(len(facts), 2) # Unique + One of the duplicates
        
    def test_nav_filtering(self):
        # Test strict filter
        self.assertFalse(_is_valid_fact("Main Menu (http://x.com)", set(), [])) # Short nav
        self.assertTrue(_is_valid_fact("Valid Content about Policy", set(), []))

if __name__ == "__main__":
    unittest.main()
