import unittest
from unittest.mock import MagicMock, patch
from src.rag.article_interpreter import ArticleInterpreter
from src.rag.article_cleaner import is_navigation_dominated, clean_article_content

class TestPhase183Unified(unittest.TestCase):

    @patch('src.rag.article_interpreter.ollama_generate')
    def test_case_1_asr920_unified_policy(self, mock_llm):
        print("\n=== Test Case 1: ASR920 (Unified Policy + Cleaner) ===")
        # Scenario: Long command output with junk footer
        mock_llm.return_value = "บทความนี้รวบรวมคำสั่ง ASR920 สำหรับการตรวจสอบสถานะ"
        
        ux_cfg = {
            "article.max_chars": 900,
            "article.intro.enabled": True,
            "article.intro.max_chars": 220
        }
        interpreter = ArticleInterpreter(llm_cfg={"model": "test"}, ux_cfg=ux_cfg)
        
        raw_content = """
        ASR920 Command List
        show platform
        show version
        ... (imagine 2000 chars of commands) ...
        
        ศูนย์ปฏิบัติการ (NOC)
        Service Management Center(SMC)
        ผู้ดูแลระบบ
        """
        # Cleaner logic is called inside interpret usually, but let's verify integration
        # Note: clean_article_content is called inside interpret
        
        url = "http://nt.com/asr920"
        ans = interpreter.interpret("ASR920 command", "ASR920-12GE", url, raw_content * 20) # Make it VERY long (> 3000 chars)
        
        print(f"Answer:\n{ans[:500]}...\n...{ans[-300:]}")
        
        # Verify Structure
        self.assertIn("บทความนี้รวบรวมคำสั่ง", ans) # Intro
        self.assertIn("ASR920 Command List", ans) # Excerpt
        self.assertIn("📌 อ่านเพิ่มเติม:", ans) # Footer (since truncated)
        self.assertNotIn("Service Management Center(SMC)", ans) # Cleaner worked
        
    def test_case_2_edimax_not_nav(self):
        print("\n=== Test Case 2: EDIMAX (Not Nav Page) ===")
        # Scenario: Short-ish How-to (350 chars)
        
        content = """
        วิธีแก้ไขปัญหา EDIMAX โดน Hack
        1. Login เข้า router
        2. ไปที่ System Maintenance
        3. เปลี่ยน Password
        4. ตั้งค่า DNS เป็น 8.8.8.8
        การตั้งค่านี้จะช่วยป้องกันการถูกเจาะระบบ
        """
        # Intent words: วิธี, การตั้งค่า
        # Length ~ 150 chars (Need to pad to test > 300 boundary if strictly followed, 
        # but our code says > 300. Let's make it > 300)
        content += "รายละเอียดเพิ่มเติม " * 20 
        
        is_nav = is_navigation_dominated(content)
        print(f"Is Nav: {is_nav}")
        self.assertFalse(is_nav, "Should NOT be Nav Page because it has How-to intent")

    @patch('src.rag.article_interpreter.ollama_generate')
    def test_case_3_tr069_unified(self, mock_llm):
        print("\n=== Test Case 3: TR069 (Intro + Preview + Footer) ===")
        mock_llm.return_value = "TR069 หรือ CWMP เป็นโปรโตคอลจัดการอุปกรณ์ระยะไกล"
        
        ux_cfg = {"article.intro.enabled": True}
        interpreter = ArticleInterpreter(llm_cfg={"model": "test"}, ux_cfg=ux_cfg)
        
        content = "Standard TR069 content... " * 50
        url = "http://nt.com/tr069"
        
        ans = interpreter.interpret("TR069 คือ", "TR069 Intro", url, content)
        
        self.assertIn("TR069 หรือ CWMP", ans) # Intro
        self.assertIn("📌", ans) # Footer
        
    def test_case_4_bridge_footer_source(self):
        print("\n=== Test Case 4: Bridge (Short Article -> Header Footer) ===")
        # Scenario: Short article not truncated
        ux_cfg = {"article.max_chars": 5000} # Large limit
        interpreter = ArticleInterpreter(llm_cfg={"model": "test"}, ux_cfg=ux_cfg)
        
        content = "วิธีการทำ Bridge Mode บน Cisco Router... (Short content)"
        url = "http://nt.com/bridge"
        
        # Mock LLM skipping for short content? No, logic calls LLM implies Intro always if enabled
        # If we disable intro for short? No, unified policy says Intro + Preview
        # Let's mock LLM simply
        with patch('src.rag.article_interpreter.ollama_generate', return_value="สรุปการทำ Bridge Mode"):
             ans = interpreter.interpret("Bridge Mode", "Cisco Bridge", url, content)
        
        print(f"Answer:\n{ans}")
        self.assertIn("📌 แหล่งที่มา:", ans) # Short footer (not truncated)

if __name__ == '__main__':
    unittest.main()
