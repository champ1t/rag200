
import unittest
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleInterpreterJunkTable(unittest.TestCase):
    def test_junk_table_content(self):
        # Mock Config
        llm_cfg = {"model": "mock-model", "base_url": "http://localhost:11434"}
        interpreter = ArticleInterpreter(llm_cfg)
        
        # Scenario: Long text (> 600 chars) BUT full of pipe garbage and numbers
        # 100 * 7 chars = 700 chars
        junk_text = "| 123 | 456 | 789 | " * 50 
        images = [{"url": "http://test.com/scan.jpg", "alt": "Scan"}]
        
        url = "http://test.com/news/junk"
        query = "ขอรายละเอียด"
        
        result = interpreter.interpret(query, "Junk Article", url, junk_text, images=images)
        
        print(f"\n[Test Result] Output:\n{result}\n")
        
        # Assertions
        # Expect the warning message about image/scan content
        self.assertIn("ข้อมูลเรื่องนี้ถูกจัดเก็บในรูปแบบรูปภาพ/ไฟล์สแกน", result)
        self.assertIn("แหล่งที่มา", result)
        self.assertNotIn("123", result) # Should NOT output the junk text

if __name__ == "__main__":
    unittest.main()
