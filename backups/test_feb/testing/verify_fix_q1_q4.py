
import sys
import os
import unittest

# Add project root to path (so 'src' is importable)
sys.path.append(os.getcwd())
try:
    from src.chat_engine import ChatEngine
except ImportError:
    # If running from src/testing, go up
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from src.chat_engine import ChatEngine

class TestFixes(unittest.TestCase):
    def setUp(self):
        import yaml
        with open("configs/config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        # Ensure we use specific testing overrides if needed, but for now real config is best
        cfg["chat"]["save_log"] = False # Disable logging to avoid clutter
        self.engine = ChatEngine(cfg)

    def test_q1_huawei_commands(self):
        query = "Huawei bras ippgw command มีอะไรบ้าง"
        print(f"\n--- Testing Q1: {query} ---")
        resp = self.engine.process(query)
        print(f"Response: {resp['answer'][:200]}...")
        print(f"Route: {resp['route']}")
        
        # Expectation: Should find Article 670
        # Should NOT be knowledge_pack
        self.assertIn(resp['route'], ['article_answer', 'rag', 'rag_answer', 'rag_clarify'])
        self.assertTrue(any(k in resp['answer'].lower() for k in ['display', 'recycle', 'lock']), "Missing command keywords in answer")

    def test_q3_support_phone(self):
        print(f"\n--- Testing Q3: เบอร์โทร Support Huawei BRAS ---")
        query = "เบอร์โทร Support Huawei BRAS"
        resp = self.engine.process(query)
        print(f"Response: {resp['answer'][:200]}...")
        print(f"Route: {resp['route']}")
        
        # Should fallback to RAG/Article since ContactHandler likely won't find it in struct data
        self.assertIn(resp['route'], ['article_answer', 'rag', 'rag_answer', 'contact_hit_role']) 
        # Content check: "092-992949" is in the article
        self.assertTrue("092" in resp['answer'] or "992949" in resp['answer'], "Missing Support Phone info")

    def test_q4_clear_ip(self):
        query = "วิธี clear ip address ลูกค้าใน IP Pool"
        print(f"\n--- Testing Q4: {query} ---")
        resp = self.engine.process(query)
        print(f"Response: {resp['answer'][:200]}...")
        print(f"Route: {resp['route']}")
        
        # Expectation: Content Cleaner fix should allow 'recycle' to be found
        self.assertTrue("recycle" in resp['answer'].lower() or "lock" in resp['answer'].lower(), "Failed to extract 'recycle/lock' command from article")

    def test_q6_adsl_content(self):
        query = "วิธี add adsl Huawei"
        print(f"\n--- Testing Q6: {query} ---")
        resp = self.engine.process(query)
        print(f"Response: {resp['answer'][:200]}...")
        print(f"Route: {resp['route']}")
        
        # Expectation: Should NOT be Link Directory (list of URLs only)
        # Should contain technical keywords like 'service-port' or 'vpi'
        self.assertIn(resp['route'], ['article_answer', 'rag_answer'])
        self.assertTrue("service-port" in resp['answer'].lower() or "vpi" in resp['answer'].lower(), "Missing 'service-port' command in ADSL guide")

if __name__ == '__main__':
    unittest.main()
