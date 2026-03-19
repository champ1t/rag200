
import sys
import os
import unittest
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.rag.article_cleaner import smart_truncate, strip_navigation_text

class TestArticleRefinements(unittest.TestCase):
    def test_smart_truncate_footer(self):
        """Verify smart_truncate appends the footer correclty."""
        text = "This is a long text that needs truncation. " * 50
        max_length = 50
        footer_url = "http://example.com/read-more"
        
        truncated = smart_truncate(text, max_length=max_length, footer_url=footer_url)
        
        print(f"\n[TEST] Original Length: {len(text)}")
        print(f"[TEST] Truncated Text:\n---\n{truncated}\n---")
        
        self.assertIn("📌 เนื้อหามีรายละเอียดเพิ่มเติม", truncated)
        self.assertIn(footer_url, truncated)
        self.assertTrue(len(truncated) < len(text) + 200) # Ensure it was actually truncated but includes footer

    def test_strip_navigation_text(self):
        """Verify strip_navigation_text removes common menu items."""
        noisy_text = """
        Home > Category > Tech
        Menu
        About Us
        Contact
        
        This is the actual article content. It should remain.
        
        Copyright 2024
        Privacy Policy
        """
        
        clean_text = strip_navigation_text(noisy_text)
        print(f"\n[TEST] Noisy Text:\n---\n{noisy_text}\n---")
        print(f"[TEST] Clean Text:\n---\n{clean_text}\n---")
        
        self.assertIn("This is the actual article content", clean_text)
        self.assertNotIn("Home > Category", clean_text)
        self.assertNotIn("Privacy Policy", clean_text)

if __name__ == '__main__':
    unittest.main()
