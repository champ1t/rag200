import unittest
from unittest.mock import MagicMock, patch
from src.rag.article_interpreter import ArticleInterpreter
from src.rag.article_cleaner import is_navigation_dominated

class TestPhase175LongArticle(unittest.TestCase):
    
    def test_nav_fix_rule1_howto(self):
        print("\n=== Test Nav Fix Rule 1: Long How-to ===")
        # Content > 500 chars with "How-to" keywords should NOT be Nav, even if link density is high
        
        long_howto = "วิธีใช้งานระบบ (How-to)\n" + "เนื้อหายาวๆ "*50 + "\n"
        # Add many links to trigger density check
        for i in range(20):
            long_howto += f"[Link {i}](http://example.com/{i})\n"
            
        print(f"Content Length: {len(long_howto)}")
        is_nav = is_navigation_dominated(long_howto)
        print(f"Is Navigation? {is_nav}")
        self.assertFalse(is_nav, "Should NOT be navigation because it has 'วิธี' and length > 500")

    def test_nav_fix_rule2_paragraphs(self):
        print("\n=== Test Nav Fix Rule 2: Paragraphs ===")
        # Content with 2+ distinct paragraphs should NOT be Nav
        
        para_content = "Paragraph 1 is long enough to count as content.... " * 5 + "\n\n"
        para_content += "Paragraph 2 is also long enough.... " * 5 + "\n\n"
        # Add noise
        para_content += "Menu 1\nMenu 2\nMenu 3\n"
        
        is_nav = is_navigation_dominated(para_content)
        print(f"Is Navigation? {is_nav}")
        self.assertFalse(is_nav, "Should NOT be navigation because it has 2+ paragraphs")
        
    @patch('src.rag.article_interpreter.ollama_generate')
    def test_policy_1_tutorial_summary(self, mock_llm):
        print("\n=== Test Policy 1: Tutorial Summary ===")
        # Setup
        interpreter = ArticleInterpreter(llm_cfg={"model": "test"}, ux_cfg={})
        mock_llm.return_value = "- Summary Point 1\n- Summary Point 2"
        
        # Query that triggers Tutorial Mode
        query = "วิธีแก้ปัญหา tr069 คืออะไร" 
        
        # Long content
        content = "Intro\n\n" + "Content " * 500
        url = "http://nt-knowledge.com/tr069"
        
        ans = interpreter.interpret(query, "TR069 Fix", url, content)
        
        print(f"Answer:\n{ans}")
        
        # Verify
        self.assertIn("- Summary Point 1", ans)
        self.assertIn("📌 อ่านขั้นตอนทั้งหมดได้ที่:", ans)
        self.assertIn(url, ans)
        
    def test_policy_2_excerpt_config_excerpt_mode(self):
        print("\n=== Test Policy 2: Excerpt Config (Mode=Excerpt) ===")
        # Setup
        ux_config = {
            "long_article_mode": "excerpt",
            "long_article_max_chars": 2000
        }
        interpreter = ArticleInterpreter(llm_cfg={"model": "test"}, ux_cfg=ux_config)
        
        # Query that is Technical (Type A) but NOT Tutorial
        query = "Show run config interface"
        
        # Long content with structure
        content = "interface GigabitEthernet0/0\n description WAN\n ip address 1.2.3.4\n" * 100
        url = "http://nt-knowledge.com/config"
        
        ans = interpreter.interpret(query, "Switch Config", url, content)
        
        print(f"Answer Head:\n{ans[:200]}...")
        # Verify
        self.assertIn("(แสดงเนื้อหาบางส่วน", ans)
        self.assertIn("📌 อ่านเพิ่มเติม:", ans)
        
    def test_cleaner_noise_removal(self):
        print("\n=== Test Cleaner Noise Removal ===")
        from src.rag.article_cleaner import clean_article_content
        
        raw = """
        เนื้อหาจริง
        ศูนย์ปฏิบัติการ (NOC)
        Service Management Center(SMC)
        ผู้ดูแลระบบ
        กองทุนสำรองฯ
        """
        cleaned = clean_article_content(raw)
        print(f"Cleaned:\n{cleaned}")
        
        self.assertNotIn("Service Management Center(SMC)", cleaned)
        self.assertNotIn("ผู้ดูแลระบบ", cleaned)
        self.assertIn("เนื้อหาจริง", cleaned)

if __name__ == '__main__':
    unittest.main()
