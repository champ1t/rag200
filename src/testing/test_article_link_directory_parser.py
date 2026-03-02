import unittest
from unittest.mock import MagicMock
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleLinkDirectoryParser(unittest.TestCase):
    def setUp(self):
        # Mock LLM Config
        self.mock_cfg = {"base_url": "mock", "model": "mock", "llm": {}}
        self.interpreter = ArticleInterpreter(self.mock_cfg)

    def test_detection(self):
        """Test detection logic."""
        # Case 1: Pure Directory
        content_dir = "Link 1: ftp://1.2.3.4\nLink 2: ftp://5.6.7.8\nLink 3: http://google.com\nLink 4: https://test.com\nLink 5: ftp://a.b\nLink 6: ftp://c.d\nLink 7: ftp://e.f"
        self.assertTrue(self.interpreter._looks_like_link_directory(content_dir))
        
        # Case 2: Mixed Manual
        content_manual = "FTTx Manual (ftp://1.2.3.4)\nNIS Manual (ftp://5.6.7.8)\nGuide (http://...)\nSome text."
        self.assertTrue(self.interpreter._looks_like_link_directory(content_manual))
        
        # Case 3: Normal Article
        content_normal = "This is a normal news article about SMC. No heavy links."
        self.assertFalse(self.interpreter._looks_like_link_directory(content_normal))

    def test_parser_id576_sample(self):
        """Test parsing of the specific troublesome article ID 576."""
        # Simulated content based on user description (noisy table artifacts)
        # Note: In reality, article_cleaner might have stripped some HTML, but table borders `| | |` might remain.
        sample_content = """
        FTTx and NIS Manual
        | | |
        |---|---|
        1. NIS Manual
        TOT NIS Overview (ftp://10.192.133.33/manual/NIS/TOT_NIS_Overview.pdf)
        NetkaView Network Manager (ftp://10.192.133.33/manual/NIS/NetkaView.pdf)
        
        2. FTTxSM Manual
        FTTxSM User Manual (ftp://10.192.133.33/manual/FTTx/UserManual.pdf)
        
        | | |
        3. Fiberhome Manual
        คู่มือ config Fiberhome (https://drive.google.com/open?id=123)
        
        Footer:
        ศูนย์ปฏิบัติการ SMC ภาคเหนือ
        """
        
        ans = self.interpreter._parse_link_directory(sample_content, "FTTx and NIS Manual")
        
        print("\n[Parsed Output]:\n", ans)
        
        # Checks
        self.assertIn("[FTTx and NIS Manual]", ans)
        self.assertIn("**NIS Manual**", ans)
        self.assertIn("**FTTxSM Manual**", ans)
        self.assertIn("**Fiberhome Manual**", ans)
        
        # Check Links
        self.assertIn("- [TOT NIS Overview](ftp://10.192.133.33/manual/NIS/TOT_NIS_Overview.pdf)", ans)
        self.assertIn("- [NetkaView Network Manager](ftp://10.192.133.33/manual/NIS/NetkaView.pdf)", ans)
        
        # Check Noise Filtering
        self.assertNotIn("| | |", ans)
        self.assertNotIn("ศูนย์ปฏิบัติการ", ans) # Footer should be filtered or ignored
        
    def test_parser_markdown_links(self):
        """Test parsing of already markdown-formatted links."""
        content = """
        Manual Section
        - [Link A](http://a.com)
        - [Link B](http://b.com)
        """
        ans = self.interpreter._parse_link_directory(content, "Test Markdown")
        self.assertIn("- [Link A](http://a.com)", ans)
        self.assertIn("**Manual Section**", ans)

if __name__ == "__main__":
    unittest.main()
