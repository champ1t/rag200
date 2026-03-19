
import sys
import unittest
sys.path.append(".")

from src.rag.article_cleaner import smart_truncate

class TestDirectPreview(unittest.TestCase):
    def test_smart_truncate_short(self):
        """If text < limit, return as is (no footer unless forced?)"""
        # Note: function sig is (text, max_length, footer_url)
        # If footer_url is empty, no footer. If provided, footer is added ONLY ??
        # Wait, if text < limit, we might NOT want footer if it's the WHOLE text?
        # User says: "📌 เนื้อหามีรายละเอียดเพิ่มเติม" implies there is *more*.
        # If we show everything, maybe we just show "Source: ..." or nothing.
        # But the code adds footer if footer_url is provided, regardless of truncation?
        # Let's check logic:
        # return final_text + footer (if footer_url provided)
        # So it always adds footer. This fits "Standardized Footer" requirement.
        
        text = "Short text."
        res = smart_truncate(text, 1000, "http://test.com")
        self.assertIn("Short text.", res)
        self.assertIn("Short text.", res)
        self.assertIn("📌 แหล่งที่มา", res)
        self.assertIn("http://test.com", res)
        self.assertIn("http://test.com", res)

    def test_smart_truncate_long(self):
        """Should truncate safely"""
        # Create paragraphs
        para1 = "A" * 400
        para2 = "B" * 400
        para3 = "C" * 400
        full_text = f"{para1}\n\n{para2}\n\n{para3}"
        
        # Limit 600. Should keep para1, maybe para2 if it fits?
        # 400 + 400 = 800. 800 > 600+200? No. (800 <= 800).
        # So it might include para2.
        # Let's try limit 500.
        # 400 (ok). Next is 400. 400+400 = 800.
        # 800 > 500 + 200 (700). Yes.
        # So it should stop after para1.
        
        res = smart_truncate(full_text, max_length=500, footer_url="http://long.com")
        
        self.assertIn(para1, res)
        self.assertNotIn(para3, res)
        # para2 should be excluded because 800 > 700
        self.assertNotIn("BBBB", res)
        self.assertIn("📌", res)

if __name__ == "__main__":
    unittest.main()
