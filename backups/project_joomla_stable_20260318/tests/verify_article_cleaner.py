
import unittest
from src.rag.article_cleaner import smart_truncate, strip_navigation_text

class TestArticleRefinements(unittest.TestCase):
    def test_smart_truncate_read_more(self):
        """Test that smart_truncate appends the footer when provided."""
        text = "This is a long article content that needs to be truncated. " * 50
        max_length = 100
        footer_url = "https://example.com/article"
        
        truncated = smart_truncate(text, max_length, footer_url=footer_url)
        
        print(f"\n[TEST] Truncated Text:\n{truncated}")
        
        self.assertIn("📌 เนื้อหามีรายละเอียดเพิ่มเติม", truncated)
        self.assertIn(footer_url, truncated)
        self.assertTrue(len(truncated) < len(text) or len(text) < max_length + 200) # +200 for footer

    def test_strip_navigation_text(self):
        """Test that strip_navigation_text removes common UI noise."""
        noisy_text = """
        Home > Category > Tech
        User Menu
        Settings
        Logout
        
        This is the actual article content that we want to keep.
        It has some interesting information.
        
        Copyright 2024 Example Corp.
        Privacy Policy
        Terms of Service
        """
        
        clean_text = strip_navigation_text(noisy_text)
        
        print(f"\n[TEST] Cleaned Text:\n{clean_text}")
        
        self.assertNotIn("User Menu", clean_text)
        self.assertNotIn("Logout", clean_text)
        self.assertNotIn("Copyright 2024", clean_text)
        self.assertIn("This is the actual article content", clean_text)

if __name__ == "__main__":
    unittest.main()
