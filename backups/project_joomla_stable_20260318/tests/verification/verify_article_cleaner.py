
import sys
import unittest
from unittest.mock import MagicMock

# Adjust path to include src
sys.path.append('.')

from src.rag.article_cleaner import smart_truncate, strip_navigation_text

class TestArticleEnhancements(unittest.TestCase):
    def test_smart_truncate_footer(self):
        """Test that smart_truncate appends the footer functionality."""
        text = "This is a long article content. " * 50
        footer_url = "https://example.com/article"
        
        # Truncate to a small length to force truncation
        truncated = smart_truncate(text, max_length=100, footer_url=footer_url)
        
        print(f"\n[TEST] Input Length: {len(text)}")
        print(f"[TEST] Truncated Length: {len(truncated)}")
        print(f"[TEST] Truncated output: {truncated[-100:]}") # Show end of string

        expected_footer = f"\n\n📌 เนื้อหามีรายละเอียดเพิ่มเติม\n🔗 อ่านต่อฉบับเต็มได้ที่:\n{footer_url}"
        self.assertIn(footer_url, truncated)
        self.assertTrue(truncated.endswith(footer_url))
        print("[PASS] Footer URL found in truncated text.")

    def test_strip_navigation_text(self):
        """Test that strip_navigation_text removes common noise."""
        noise = """
        Home
        About Us
        Contact
        Services
        
        Actual Article Title
        
        This is the real content.
        
        Privacy Policy
        Terms of Service
        """
        
        cleaned = strip_navigation_text(noise)
        print(f"\n[TEST] Original:\n{noise}")
        print(f"[TEST] Cleaned:\n{cleaned}")
        
        self.assertNotIn("Home", cleaned)
        self.assertNotIn("Privacy Policy", cleaned)
        self.assertIn("Actual Article Title", cleaned)
        self.assertIn("This is the real content", cleaned)
        print("[PASS] Navigation noise removed.")
        
if __name__ == '__main__':
    unittest.main()
