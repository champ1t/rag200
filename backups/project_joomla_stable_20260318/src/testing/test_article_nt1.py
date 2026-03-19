import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.chat_engine import ChatEngine

CFG = {
    "retrieval": {"top_k": 3},
    "llm": {"model": "qwen3:8b", "base_url": "http://localhost:11434"},
    "rag": {"score_threshold": 0.25},
    "chat": {"show_context": False, "save_log": False}
}

class TestArticleNT1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SETUP] Initializing ChatEngine for Article NT-1 Tests...")
        cls.engine = ChatEngine(CFG)
        
    def test_nt1_whole_article(self):
        """Test 'ข่าว NT1' returns structured article content, not just link"""
        res = self.engine.process("ข่าว NT1")
        
        # Must route to article_answer, not link_lookup
        self.assertEqual(res["route"], "article_answer")
        
        # Must contain extracted information from article
        answer = res["answer"]
        
        # Check for key information that should be in NT-1 article
        expected_items = [
            "61.19.143.4",  # IP address
            "RNOC",  # Department/system name
            "0-81417-0144",  # Phone number
            "08-1350-9735",  # Phone number
            "admin@tec",  # Username
            "122.155.137.209"  # IP address
        ]
        
        for item in expected_items:
            self.assertIn(item, answer, f"Missing expected item: {item}")
        
        print(f"\n[PASS] NT-1 Whole Article: Found {len(expected_items)} key items")
        print(f"Answer preview: {answer[:200]}...")
        
    def test_nt1_rnoc_section(self):
        """Test 'เบอร์ RNOC ข่าว NT1' returns only RNOC phone section"""
        res = self.engine.process("เบอร์ RNOC ข่าว NT1")
        
        self.assertEqual(res["route"], "article_answer")
        
        answer = res["answer"]
        
        # Must contain RNOC phone numbers
        self.assertIn("RNOC", answer)
        self.assertTrue(
            "0-81417-0144" in answer or "08-1350-9735" in answer,
            "RNOC phone numbers not found"
        )
        
        print(f"\n[PASS] NT-1 RNOC Section: {answer[:150]}...")
        
    def test_nt1_css_section(self):
        """Test 'ระบบ CSS NT1' returns CSS system info"""
        res = self.engine.process("ระบบ CSS ข่าว NT1")
        
        self.assertEqual(res["route"], "article_answer")
        
        answer = res["answer"]
        
        # Must contain CSS-related information
        # (Adjust based on actual NT-1 article content)
        self.assertIn("CSS", answer.upper())
        
        print(f"\n[PASS] NT-1 CSS Section: {answer[:150]}...")
        
    def test_nt1_session_ip(self):
        """Test 'URL ดู session ip ข่าว NT1' returns session IP URL"""
        res = self.engine.process("URL ดู session ip ข่าว NT1")
        
        self.assertEqual(res["route"], "article_answer")
        
        answer = res["answer"]
        
        # Must contain session IP URL
        self.assertTrue(
            "122.155.137.209" in answer or "session" in answer.lower(),
            "Session IP URL not found"
        )
        
        print(f"\n[PASS] NT-1 Session IP: {answer[:150]}...")
        
    def test_nt1_wireless_router(self):
        """Test 'user/pass wireless router NT1' returns credentials"""
        res = self.engine.process("user pass wireless router ข่าว NT1")
        
        self.assertEqual(res["route"], "article_answer")
        
        answer = res["answer"]
        
        # Must contain wireless router credentials
        self.assertTrue(
            "admin" in answer.lower() or "password" in answer.lower() or "user" in answer.lower(),
            "Wireless router credentials not found"
        )
        
        print(f"\n[PASS] NT-1 Wireless Router: {answer[:150]}...")
        
    def test_nt1_fast_response(self):
        """Test article_answer is reasonably fast (< 15s)"""
        import time
        
        t0 = time.time()
        res = self.engine.process("ข่าว NT1")
        duration = (time.time() - t0) * 1000
        
        self.assertEqual(res["route"], "article_answer")
        self.assertLess(duration, 15000, f"Article answer took too long: {duration:.2f}ms")
        
        print(f"\n[PASS] NT-1 Fast Response: {duration:.2f}ms")

if __name__ == "__main__":
    unittest.main()
