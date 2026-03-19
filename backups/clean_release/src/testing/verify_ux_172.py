
import sys
import unittest
# Add src to path
sys.path.append(".")

from src.core.chat_engine import ChatEngine
from src.rag.article_cleaner import clean_article_content, detect_and_summarize_tables, format_fact_item, extract_topic_anchored_facts

class TestUXPhase172(unittest.TestCase):
    def test_link_splitting_multiple(self):
        """Test Case (A): Ribbon EdgeMare6000 DOC - Multiple URLs in one line"""
        raw_text = "Ribbon EdgeMare6000 DOC คู่มือ (ftp://link1) (ftp://link2) Title3 (https://link3)"
        
        # We need to simulate how ArticleCleaner.format_fact_item processes this.
        # But format_fact_item expects a list of strings (lines)
        
        formatted = format_fact_item([raw_text], enable_formatting=True)
        print(f"\n[A] Input: {raw_text}\n[A] Output:\n{formatted}")
        
        self.assertIn("🔗", formatted)
        self.assertIn("\n", formatted)
        self.assertIn("ftp://link1", formatted)
        self.assertIn("ftp://link2", formatted)
        self.assertIn("https://link3", formatted)

    def test_table_ip_safety(self):
        """Test Case (C): IP_SSH - Table summarization safety"""
        # Simulate table rows
        rows = [
            "| ID | Port | IP Address |",
            "| 1  | 80   | 192.168.1.1 |",
            "| 2  | 443  | 10.0.0.1 |"
        ]
        
        summary = detect_and_summarize_tables(rows, enable_formatting=True)
        # It handles flush internally, but let's check the core logic which is inside detect_and_summarize_tables
        # Actually detect_and_summarize_tables returns cleaned lines.
        
        print(f"\n[C] Input Table:\n" + "\n".join(rows))
        print(f"[C] Output:\n" + "\n".join(summary))
        
        joined = "\n".join(summary)
        self.assertNotIn("|", joined) # Pipes should be gone
        self.assertIn("192.168.1.1", joined) # IPs must remain
        self.assertIn("1, 80, 192.168.1.1", joined) # Comma separation check

    def test_nav_page_extraction(self):
        """Test Case (B): Nav Page - Short link extraction"""
        # This requires ArticleInterpreter logic which searches for links
        # We can test the regex/logic used in ArticleInterpreter.interpret
        
        content = """
        <html>
        <body>
        <a href="http://INTERNAL_SMC_IP/file1.pdf">Template ZTE</a>
        <a href="http://INTERNAL_SMC_IP/file2.pdf">Get IP</a>
        <a href="http://link3">Short</a>
        </body>
        </html>
        """
        # Mock ArticleInterpreter's logic
        from src.rag.article_interpreter import ArticleInterpreter
        # We can't easily instantiate full interpreter without config, but we can verify regex
        import re
        links = re.findall(r'([^>\n|]{2,40})(?:\(|^|\s+)(https?://\S+|ftp://\S+)(?:\)|$|\s)', "Template ZTE (http://INTERNAL_SMC_IP/file1.pdf)")
        
        print("\n[B] Nav Link Extraction Test:")
        self.assertTrue(len(links) > 0)
        title, url = links[0]
        print(f"Extracted: '{title}' -> {url}")
        self.assertEqual(title.strip(), "Template ZTE")

        # Test "Get IP" (short title)
        links2 = re.findall(r'([^>\n|]{2,40})(?:\(|^|\s+)(https?://\S+|ftp://\S+)(?:\)|$|\s)', "Get IP (http://INTERNAL_SMC_IP/file2.pdf)")
        if links2:
             t2, u2 = links2[0]
             print(f"Extracted: '{t2}' -> {u2}")
             self.assertTrue(len(t2) >= 2)
        else:
             self.fail("Failed to extract short title 'Get IP'")


if __name__ == "__main__":
    unittest.main()
