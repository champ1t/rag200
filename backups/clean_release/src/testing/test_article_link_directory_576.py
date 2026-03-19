import unittest
import re
from unittest.mock import MagicMock
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleLinkDirectory576(unittest.TestCase):
    def setUp(self):
        # Mock LLM Config
        self.mock_cfg = {"base_url": "mock", "model": "mock", "llm": {}}
        self.interpreter = ArticleInterpreter(self.mock_cfg)
        
        # Simulated content for Article 576 (FTTx and NIS Manual)
        # Includes:
        # - Numbered lists (triggering old fast-path)
        # - Table noise | | |
        # - Footer noise (SMC)
        # - Wrapped URLs/Lines
        self.content_576 = """
        FTTx and NIS Manual
        | | |
        เขียนโดย Administrator | แก้ไขล่าสุดเมื่อ วันอังคารที่ ...
        
        1. NIS Manual
        TOT NIS Overview (ftp://INTERNAL_SMC_IP/manual/NIS/TOT_NIS_Overview.pdf)
        NetkaView Network Manager (ftp://INTERNAL_SMC_IP/manual/NIS/NetkaView.pdf)
        
        2. FTTxSM Manual
        FTTxSM User Manual (ftp://INTERNAL_SMC_IP/manual/FTTx/
        UserManual.pdf)
        มาตรฐาน ODN (ftp://INTERNAL_SMC_IP/WorkP4/TOTODNStandard.pdf)
        
        | | |
        3. Fiberhome Manual
        คู่มือ config Fiberhome (https://drive.google.com/file/d/1YmCYQ78hI8fgiePxe-u9bzX6Y0y_tkCb/view?usp=sharing)
        
        Footer:
        ศูนย์ปฏิบัติการระบบสื่อสารข้อมูล (สบลตน.)
        Service Management Center(SMC)
        """

    def test_directory_priority_and_format(self):
        """Test strict formatting: No '[News Article]', Bullets = 'Title (URL)', No '|'."""
        
        # Test detection
        is_dir = self.interpreter._looks_like_link_directory(self.content_576)
        self.assertTrue(is_dir, "Should be detected as Link Directory")
        
        ans = self.interpreter._parse_link_directory(self.content_576, "FTTx and NIS Manual")
        print("\n[Parsed Output 576]:\n", ans)
        
        # 1. Check Header Structure: "**Title**" but NO "[News Article]" wrapper
        self.assertNotIn("[News Article]", ans, "Should not have '[News Article]' wrapper")
        self.assertNotIn("|", ans, "Should have stripped all pipes '|'")
        
        # 2. Check Bullet Format: "Title (URL)" NOT "[Title](URL)"
        # We want plain text bullets for these directory pages to avoid giant-link issues
        # Regex for Markdown Link: \[.*?\]\(.*?\)
        # We want to Ensure we DON'T have them in the items
        # But wait, User Request said: "Append as plain bullet with 'Title (URL)' not markdown link."
        
        # Let's count standard markdown links vs plain text " (http"
        md_links = re.findall(r'\[.*?\]\(http.*?\)', ans)
        plain_links = re.findall(r'[^\)\]] \(http.*?\)', ans) # Space + (http...
        
        # We enforce ZERO markdown links for the ITEMS (we might allow Source link at bottom)
        # Actually user said "Prevent giant-link bugs". 
        # "Use 'title (url)'"
        
        # We'll check that specific known items are NOT markdown links
        self.assertNotIn("[NIS Manual]", ans) 
        self.assertIn("NIS Manual", ans)
        
        # Check specific items
        self.assertIn("TOT NIS Overview (ftp://INTERNAL_SMC_IP/manual/NIS/TOT_NIS_Overview.pdf)", ans)
        self.assertIn("NetkaView Network Manager (ftp://INTERNAL_SMC_IP/manual/NIS/NetkaView.pdf)", ans)
        self.assertIn("FTTxSM User Manual (ftp://INTERNAL_SMC_IP/manual/FTTx/UserManual.pdf)", ans)
        
        # 3. Check Grouping
        self.assertIn("**NIS Manual**", ans)
        self.assertIn("**FTTxSM Manual**", ans)
        self.assertIn("**Fiberhome Manual**", ans)
        
        # 4. Check Splitting of Inline Headers
        # "2. FTTxSM Manual" should be on its own line (header), not part of previous item
        # Input had: "2. FTTxSM Manual" on new line, but "1. NIS Manual" line had content?
        # Input: "1. NIS Manual\nTOT NIS Overview..." -> OK.
        # But Phase 79 requires splitting "1. A 2. B" on single line.
        # Let's add a single line test case.
        
    def test_inline_split_logic(self):
        """Test splitting of content like '1. A 2. B 3. C' specifically for Directory Parser normalization."""
        messy_line = "1. Item A (http://a) 2. Item B (http://b) 3. Section Header 3.1 Item C (http://c)"
        # This logic hasn't been implemented yet in Interpreter (only in Cleaner).
        # We need to implement `normalize_numbered_list` in Interpreter too.
        
        # For now, just test the main function behavior if we feed it this line wrapped in context
        content = f"""
        Messy Manual
        {messy_line}
        """
        ans = self.interpreter._parse_link_directory(content, "Messy Manual")
        print("\n[Messy Block Output]:\n", ans)
        
        self.assertIn("Item A (http://a)", ans)
        self.assertIn("Item B (http://b)", ans)
        self.assertIn("Item C (http://c)", ans)

if __name__ == "__main__":
    unittest.main()
