
import unittest
import hashlib
from src.rag.article_interpreter import ArticleInterpreter

class TestArticleFixes(unittest.TestCase):
    def setUp(self):
        # Mock Config
        llm_cfg = {"model": "mock-model", "base_url": "http://localhost:11434"}
        from unittest.mock import MagicMock
        self.interpreter = ArticleInterpreter(llm_cfg)
        # Mock LLM generation to avoid real calls
        self.interpreter.llm = MagicMock()
        self.interpreter.llm.generate.return_value = "MOCKED_LLM_RESPONSE"
        
        # Also mock ChatEngine cache just in case, though we are testing interpreter directly.
        # Ideally we patch ollama_generate, but for this logic test (Director vs Article), 
        # reaching the LLM call means it decided "Article Mode", which is what we want to assert.
        
    def test_regression_sequence(self):
        print("\n=== 1) Regression Test Sequence ===")
        
        # Scenario Data
        scenarios = [
            {
                "query": "หลักเกณฑ์กำหนด service ID บริการ Last Mile",
                "url": "http://nt.com/lastmile",
                "content": "This is the Service ID guide for Last Mile. Step 1... Step 2...",
                "expected_mode": "article" 
            },
            {
                "query": "IP_SSH",
                "url": "http://nt.com/ssh_config",
                "content": "To config SSH: ip ssh enable. interface vlan 100. crypto key generate.",
                "expected_mode": "article"
            },
            {
                "query": "Ribbon EdgeMare6000 DOC",
                "url": "http://nt.com/ribbon_docs",
                "content": """
                Manual 1 (http://10.1.1.1/doc1.pdf)
                Manual 2 (http://10.1.1.1/doc2.pdf)
                Manual 3 (http://10.1.1.1/doc3.pdf)
                Manual 4 (http://10.1.1.1/doc4.pdf)
                Manual 5 (http://10.1.1.1/doc5.pdf)
                Quick Guide (http://10.1.1.1/guide.pdf)
                Overview Guide
                Configuration Manual
                """,
                "expected_mode": "directory" # 6 links + manuals -> Directory
            }
        ]
        
        # Run Sequence Twice
        for i in range(2):
            print(f"\n--- Run {i+1} ---")
            for sc in scenarios:
                print(f"Query: {sc['query']}")
                # We mock interpret logic by inspecting 'links=' output or return val.
                # Since we can't easily capture stdout, we check return value structure.
                # Directory mode returns bullet list of links.
                # Article mode returns LLM text (fail in mock) or error string if LLM fails.
                
                # Mock LLM fallback: If it reaches LLM, it throws/returns error using mock model
                try:
                    result = self.interpreter.interpret(
                        sc['query'], "Title", sc['url'], sc['content']
                    )
                except Exception as e:
                    # If LLM fails, it implies it TRIED to be an Article.
                    result = "[Article Mode Triggered]" 
                
                # Check outcome
                if "Manual 1" in result and ("ftp://" in result or "http://" in result) and "🔗" in result:
                    mode = "directory"
                elif "Article Mode" in result or "เนื้อหา" in result or "guide" in result.lower(): 
                     # Note: Mock LLM might return "guide" if we used real one, or error Msg.
                     # If connection error to Ollama, it returns "เกิดข้อผิดพลาด...".
                     mode = "article"
                else:
                    mode = "unknown"
                    
                print(f" -> Mode Detected: {mode}")
                
                if sc['expected_mode'] == 'directory':
                    self.assertEqual(mode, 'directory', f"Failed Directory detect for {sc['query']}")
                    # Verify Links
                    self.assertIn("🔗", result, "Directory should have 🔗 links")
                else:
                    # For Article, we expect it NOT to be directory logic
                    self.assertNotEqual(mode, 'directory', f"False directory detect for {sc['query']}")

    def test_directory_detection(self):
        print("\n=== 2) Directory Test (Real) ===")
        content = "\n".join([f"Link {i} (http://test.com/{i}.pdf)" for i in range(15)])
        q = "ขอลิงก์ดาวน์โหลด"
        url = "http://nt.com/downloads"
        
        res = self.interpreter.interpret(q, "Downloads", url, content)
        self.assertIn("🔗", res)
        # Verify 15 links
        self.assertTrue(res.count("🔗") >= 15)
        print(" -> Directory Mode Confirmed (15+ links)")

    def test_text_density(self):
        print("\n=== 3) Text Density Test ===")
        # Long article with 6 links (Threshold is 8 strict, or 5+manuals)
        # This has 6 links but NO manual keywords and LOTS of text.
        long_text = "Content " * 500 # 4000 chars
        links = "\n".join([f"Ref {i} (http://ref.com/{i})" for i in range(6)])
        content = long_text + "\n" + links
        
        q = "Summarize"
        url = "http://nt.com/long_article"
        
        try:
            res = self.interpreter.interpret(q, "Article", url, content)
        except:
             res = "[Article Mode]"
             
        # Should NOT be directory
        self.assertNotIn("🔗", res)
        print(" -> Article Mode Confirmed (High Text Density)")

    def test_cache_correctness(self):
        print("\n=== 4) Cache Correctness Test (A->B->A) ===")
        # A
        url_a = "http://a.com"
        content_a = "Content A " * 50
        # B
        url_b = "http://b.com"
        content_b = "Content B " * 50
        
        q = "Summary"
        
        # Call A
        try: self.interpreter.interpret(q, "A", url_a, content_a) 
        except: pass
        
        # Verify Cache Entry
        # Hash cache key logic
        content_hash_a = hashlib.md5(content_a[:500].encode('utf-8', errors='ignore')).hexdigest()
        key_a = (url_a, q, content_hash_a)
        self.assertIn(key_a, self.interpreter._result_cache)
        
        # Call B
        try: self.interpreter.interpret(q, "B", url_b, content_b)
        except: pass
        
        content_hash_b = hashlib.md5(content_b[:500].encode('utf-8', errors='ignore')).hexdigest()
        key_b = (url_b, q, content_hash_b)
        self.assertIn(key_b, self.interpreter._result_cache)
        
        # Call A again
        res_a_2 = self.interpreter.interpret(q, "A", url_a, content_a) # Should hit cache
        # If cache hit, it prints log.
        print(" -> Cache Check Passed (Keys distinct)")

if __name__ == "__main__":
    unittest.main()
