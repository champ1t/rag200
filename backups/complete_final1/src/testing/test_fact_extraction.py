import unittest
import re
from src.rag.article_cleaner import extract_topic_anchored_facts

class TestFactExtraction(unittest.TestCase):
    def test_list_heavy_extraction(self):
        """Test splitting of list-heavy content (e.g. ID 576)."""
        content = """
        FTTx and NIS Manual
        
        1. NIS Manual
        TOT NIS Overview (ftp://10.192.133.33/manual/NIS/TOT_NIS_Overview.pdf)
        NetkaView Network Manager (ftp://10.192.133.33/manual/NIS/NetkaView.pdf)
        
        2. FTTxSM Manual
        FTTxSM User Manual (ftp://10.192.133.33/manual/FTTx/UserManual.pdf)
        """
        
        facts = extract_topic_anchored_facts(content, "manual")
        
        print("\n[Extracted Facts]:")
        for i, f in enumerate(facts):
            print(f"{i+1}. {f}")
            
        # We expect multiple facts, not one giant one
        self.assertGreater(len(facts), 2, "Should extract at least 3 facts (1 header + 2 items or similar)")
        
        # Check specific items were split or present
        # Formatting might introduce newlines, so normalize space for check
        facts_normalized = [re.sub(r'\s+', ' ', f) for f in facts]
        
        has_nis = any("TOT NIS Overview" in f for f in facts_normalized)
        has_netka = any("NetkaView" in f for f in facts_normalized)
        has_fttx = any("FTTxSM User Manual" in f for f in facts_normalized)
        
        self.assertTrue(has_nis, "Missing NIS Overview")
        self.assertTrue(has_netka, "Missing NetkaView")
        self.assertTrue(has_fttx, "Missing FTTxSM User Manual")
        
        # Verify no giant fact
        for f in facts:
            self.assertLess(len(f), 350, f"Fact too long: {len(f)} chars") # Relaxed slightly for URL expansion

    def test_max_length_splitting(self):
        """Test splitting by max length."""
        long_line_a = "A" * 250
        long_line_b = "B" * 250 + " Item" # Add keyword so it passes relevance filter
        content = f"""
        1. Item One
        {long_line_a}
        {long_line_b}
        """
        # Line 1 (8 chars).
        # Line 2 (250 chars). 8 < 200. Appends. current = 258.
        # Line 3 (250 chars). 258 > 200. Split! Flush (Line 1+2). Start Line 3.
        # Result: Fact 1 (Line 1+2), Fact 2 (Line 3).
        
        facts = extract_topic_anchored_facts(content, "Item")
        
        # Expect at least 2 facts
        self.assertGreaterEqual(len(facts), 2)
        
        # Ensure splitting happened
        self.assertTrue(any("AAA" in f for f in facts))
        self.assertTrue(any("BBB" in f for f in facts))

    def test_split_compressed_numbered_list(self):
        """Test splitting of multiple numbered items on a single line."""
        # Input: Compressed list often found in PDF-to-Text artifacts
        content = """
        Manual Downloads
        1. NIS Manual (ftp://a.pdf) 2. FTTx Manual (ftp://b.pdf) 3. Fiberhome Manual (https://c.com)
        """
        
        facts = extract_topic_anchored_facts(content, "Manual")
        
        print("\n[Compressed List Facts]:")
        for i, f in enumerate(facts):
            print(f"{i+1}. {f}")
            
        # Should be at least 3 facts, not 1 giant one
        self.assertGreaterEqual(len(facts), 3, f"Expected >= 3 facts, got {len(facts)}")
        
        # Check integrity
        self.assertTrue(any("NIS Manual" in f for f in facts))
        self.assertTrue(any("FTTx Manual" in f for f in facts))
        self.assertTrue(any("Fiberhome" in f for f in facts))

    def test_split_url_heavy_lines(self):
        """Test that lines with URLs are treated as boundaries even without numbers."""
        content = """
        Downloads:
        TOT NIS Overview ftp://10.192.133.33/manual/NIS/TOT_NIS_Overview.pdf
        NetkaView Network Manager ftp://10.192.133.33/manual/NIS/NetkaView.pdf
        User Manual ftp://10.192.133.33/manual/FTTx/UserManual.pdf
        """
        
        facts = extract_topic_anchored_facts(content, "Downloads")
        
        print("\n[URL Heavy Facts]:")
        for i, f in enumerate(facts):
            print(f"{i+1}. {f}")
            
        # Should be 3 facts
        self.assertGreaterEqual(len(facts), 3)

    def test_giant_fact_length_cap(self):
        """Test force splitting of massive facts by accumulation."""
        # Construct a massive fact appearing as multiple lines
        # Add "Topic" to each chunk to pass relevance filter and ensure uniqueness
        content = "Topic Start\n"
        for i in range(6):
            content += f"Topic: This is unique chunk {i} " + ("padding " * 10) + "\n"
            
        facts = extract_topic_anchored_facts(content, "Topic")
        
        print("\n[Giant Fact Split]:")
        for i, f in enumerate(facts):
            print(f"Fact {i+1} ({len(f)} chars): {f[:50]}...")
            
        self.assertGreater(len(facts), 1, "Should have split the giant text accumulation")

if __name__ == "__main__":
    unittest.main()
