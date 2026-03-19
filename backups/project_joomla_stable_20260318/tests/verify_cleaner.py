
import unittest
from src.rag.article_cleaner import smart_truncate, strip_navigation_text

class TestArticleCleaner(unittest.TestCase):
    def test_smart_truncate_with_footer(self):
        text = "This is a long article content. " * 50
        max_length = 100
        footer_url = "https://example.com/full-article"
        
        truncated = smart_truncate(text, max_length, footer_url=footer_url)
        
        print(f"DEBUG: Truncated text:\n{truncated}")
        
        self.assertIn("📌 เนื้อหามีรายละเอียดเพิ่มเติม", truncated)
        self.assertIn(footer_url, truncated)
        self.assertLess(len(truncated), len(text) + 200) # Ensure it's truncated but accommodates footer

    def test_strip_navigation_text(self):
        noisy_text = """
        Home > Category > Tech
        Login | Sign Up
        
        Actual article content is here. This is what we want.
        
        Privacy Policy | Terms of Service
        Copyright 2024
        """
        
        cleaned = strip_navigation_text(noisy_text)
        print(f"DEBUG: Cleaned text:\n{cleaned}")
        
        self.assertNotIn("Home > Category > Tech", cleaned)
        self.assertNotIn("Login | Sign Up", cleaned)
        self.assertNotIn("Privacy Policy | Terms of Service", cleaned)
        self.assertIn("Actual article content is here", cleaned)

if __name__ == '__main__':
    unittest.main()
