
import unittest
from src.rag.article_cleaner import (
    is_navigation_dominated, 
    extract_executive_list, 
    second_chance_procedural_extraction
)
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleGuards(unittest.TestCase):
    def setUp(self):
        self.interpreter = ArticleInterpreter({"base_url": "mock", "model": "mock"})

    def test_wrapper_guard_logic(self):
        # Create a fake wrapper/menu page content (Need > 50% nav/short lines)
        content = """
        หน้าหลัก
        ลงทะเบียน
        ลืมรหัสผ่าน
        ข่าวสาร SMC
        ความรู้
        User Menu
        Main Menu
        Login Form
        Joomla
        Extensions
        Content
        
        บริการของเรา
        - บริการ DNS (http://example.com/dns)
        - บริการ SMTP (http://example.com/smtp)
        - บริการ Web Hosting (http://example.com/web)
        - บริการ Cloud (http://example.com/cloud)
        """
        
        # 1. Cleaner should detect as Nav Dominated
        self.assertTrue(is_navigation_dominated(content))
        
        # 2. Interpreter Logic Verification
        import re
        links = re.findall(r'(.+?)\s*\((http[s]?://\S+)\)', content)
        valid_links = []
        for title, url in links:
            t = title.strip().replace("- ", "")
            if len(t) > 5:
                valid_links.append(f"- [{t}]({url})")
                
        self.assertIn("- [บริการ DNS](http://example.com/dns)", valid_links)
        
    def test_executive_list_extraction(self):
        content = """
        รายชื่อผู้บริหาร
        1. นายสมชาย ใจดี (ผจก.ส่วนงาน)
        2. นางสาวสมหญิง จริงใจ (ผส.ส่วนงาน)
        3. system admin
        4. login button
        """
        execs = extract_executive_list(content)
        self.assertTrue(len(execs) >= 2)
        self.assertIn("นายสมชาย ใจดี", execs[0])
        self.assertIn("นางสาวสมหญิง", execs[1])
        # Should filter noise
        self.assertFalse(any("login" in e for e in execs))

    def test_second_chance_recovery(self):
        # Content with nav noise BUT a valid procedure
        content = """
        หน้าหลัก
        ลงทะเบียน
        ลืมรหัสผ่าน
        User Menu
        Main Menu
        Login Form
        Joomla
        Extensions
        
        การจัดทำรายงานประจำวัน
        1. ให้ดาวน์โหลดแบบฟอร์มที่ http://form.com
        2. กรอกข้อมูลให้ครบถ้วน
        3. ส่ง mail ไปที่ admin@nt.com ภายใน 17.00 น.
        """
        # Cleaner logic check
        self.assertTrue(is_navigation_dominated(content)) 
        
        # Recovery check
        recovered = second_chance_procedural_extraction(content)
        self.assertIn("ดาวน์โหลดแบบฟอร์ม", recovered)
        self.assertIn("ส่ง mail", recovered)

if __name__ == "__main__":
    unittest.main()
