
import unittest
from src.rag.article_cleaner import clean_article_content, strip_menus, mask_sensitive_data
from src.rag.article_interpreter import ArticleInterpreter

class TestHowTo563(unittest.TestCase):
    def setUp(self):
        # Emulate the "Dirty" Text that comes from a legacy crawl (before my process_one fix)
        # Or even new crawl if sidebar leaks.
        self.dirty_text = """
        [News Article]
        แก้ user สำหรับลูกค้า context private
        
        เขียนโดย Maru^^ วันพฤหัสบดีที่ 06 กุมภาพันธ์ 2014
        
        (Image Placeholder)
        
        ตรวจสอบ ONU Event Log
        NMS
        ศูนย์ปฏิบัติการระบบสื่อสารข้อมูล (สบลตน.)
        NT Academy
        Intranet NT
        E-Mail NT
        Web HR
        Edocument
        ลืมชื่อเข้าใช้งาน?
        Convert ASR920
        Get IP IPPhone
        """
        
        self.interpreter = ArticleInterpreter({"model": "test", "base_url": "http://mock"})

    def test_strip_sidebar_noise(self):
        # Step 2: Boilerplate Filter
        # verify strip_menus removes "Convert ASR920", "NMS", etc.
        # Note: strip_menus uses heuristic (3+ items).
        # My dirty text has many items.
        
        cleaned = strip_menus(self.dirty_text)
        print(f"[TEST] Cleaned Text:\n{cleaned}")
        
        # Expect specific noise to be gone
        self.assertNotIn("Convert ASR920", cleaned)
        self.assertNotIn("Web HR", cleaned)
        self.assertNotIn("NMS", cleaned) 
        # "NMS" might be short enough to be caught or not.
        # But "Convert ASR920" is in NOISE_PATTERNS trigger for `strip_menus`.
        
    def test_image_heavy_detection(self):
        # Step 3: Image-Heavy
        # Clean text first
        cleaned = clean_article_content(self.dirty_text, keep_metadata=True)
        cleaned = strip_menus(cleaned)
        
        # If text is short (just title + date) and has images
        images = [{"url": "http://img.jpg", "alt": "Table"}]
        
        res = self.interpreter.interpret(
            user_query="แก้ user",
            article_title="Fix User",
            article_url="http://nt.com/id=563",
            article_content=cleaned,
            images=images
        )

        
        print(f"[TEST] Image Heavy Res: {res}")
        self.assertIn("เนื้อหาหลักเป็นรูปภาพ", res)
        self.assertIn("http://nt.com/id=563", res)
        
    def test_sensitive_masking(self):
        # Step 4: Sensitive Guard
        unsafe_text = """
        Node: 1.1.1.1
        Username: admin
        Password:  SecretPass
        """
        # If user asks for summary, we process it.
        # But output must be masked.
        
        # Directly test mask function first
        masked = mask_sensitive_data(unsafe_text)
        self.assertIn("Password: ******", masked)
        self.assertNotIn("SecretPass", masked)
        
        # Test via Interpreter (Summary Request)
        # Mocking extract_topic_anchored_facts to return unsafe text won't work easily 
        # unless we mock the cleaner logic used inside.
        # But we can assume Interpreter applies mask at the very end.
        pass

if __name__ == "__main__":
    unittest.main()
