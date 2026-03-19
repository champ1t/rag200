
import sys
import unittest
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleInterpreterImages(unittest.TestCase):
    def test_image_heavy_content(self):
        # Mock Config
        llm_cfg = {"model": "mock-model", "base_url": "http://localhost:11434"}
        interpreter = ArticleInterpreter(llm_cfg)
        
        # Scenario: Short text (< 600 chars) + Images Present
        # This matches the condition I modified in article_interpreter.py
        short_text = "This is a very short text that represents an announcement banner or a scanned document caption."
        images = [{"url": "http://test.com/img1.jpg", "alt": "Announcement"}]
        
        url = "http://test.com/news/123"
        query = "ขอรายละเอียดประกาศ"
        
        result = interpreter.interpret(query, "Test Announcement", url, short_text, images=images)
        
        print(f"\n[Test Result] Output:\n{result}\n")
        
        # Assertions
        # Expect the warning message about image/scan content
        self.assertIn("ข้อมูลเรื่องนี้ถูกจัดเก็บในรูปแบบรูปภาพ/ไฟล์สแกน", result)
        self.assertIn("แหล่งที่มา", result)
        self.assertNotIn("mock-model", result) # Should NOT call LLM

if __name__ == "__main__":
    unittest.main()
