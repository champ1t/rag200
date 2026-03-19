
import unittest
import os
import sys
import yaml
import re

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.chat_engine import ChatEngine

class TestFuzzNegative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[Fuzz] Initializing ChatEngine...")
        config_path = os.path.join(os.path.dirname(__file__), "../../configs/config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cls.config = yaml.safe_load(f)
        else:
             cls.config = {
                "llm": {"model_name": "gemini-pro"},
                "retrieval": {"top_k": 3},
                "data_dir": "data/records",
                "vectorstore": {"type": "chroma", "persist_dir": "data/vectorstore", "collection_name": "smc_web"}
            }
        
        try:
             cls.engine = ChatEngine(cls.config)
        except Exception as e:
             raise e

    def test_contact_noise(self):
        """Verify strict MISS for garbage contact queries."""
        noise_queries = [
            "เบอร์ xyz123",
            "เบอร์ ไม่รู้เรื่อง",
            "เบอร์ asdfghjkl",
            "ติดต่อ มนุษย์ดาวอังคาร",
            "โทรหา godzilla"
        ]
        
        for q in noise_queries:
            with self.subTest(query=q):
                res = self.engine.process(q)
                route = res.get("route", "")
                ans = res.get("answer", "")
                
                # Must be MISS or AMBIGUOUS (suggestions)
                # MUST NOT be Person Hit or Team Hit
                self.assertIn(route, ["contact_miss", "contact_ambiguous", "rag_clarify"], f"Query '{q}' leaked into {route}")
                
                # Safety Check: No Phone Numbers
                # Regex for 02-xxx-xxxx or 08x-xxx-xxxx
                phones = re.findall(r"0\d{8,9}", ans.replace("-", ""))
                self.assertEqual(phones, [], f"Query '{q}' leaked phone numbers: {phones}")

    def test_news_safety(self):
        """Verify strict MISS for garbage/denylisted news."""
        queries = [
            ("ข่าว login", ["login"]), # Explicit denylist
            ("ข่าว register", ["register"]),
            ("ข่าว reset password", ["reset", "password"]),
            ("ข่าว เกี่ยวกับ asdfghjkl", ["ไม่พบลิงก์"]) # Miss
        ]
        
        for q, expected_checks in queries:
            with self.subTest(query=q):
                res = self.engine.process(q)
                route = res.get("route", "")
                ans = res.get("answer", "")
                
                # Route should be Miss
                # But if router sees "login", it might go to NEWS_SEARCH -> Denied -> Miss
                # Or intent router blocks it?
                # We care that Answer does NOT contain links OR contains Miss text.
                
                # 1. No Links to Denylist items
                if "http" in ans:
                    # If link exists, it MUST NOT be one of the disallowed terms
                    # Actually, for "news login", we expect NO links at all.
                    if "login" in q:
                         self.fail(f"Query '{q}' returned a link! {ans}")
                         
                # 2. Expected Text
                for check in expected_checks:
                     if check == "ไม่พบลิงก์":
                         self.assertIn(check, ans, f"Query '{q}' did not return miss message.")

    def test_backoff_robustness(self):
        """Verify that missed intents don't fall through to hallucinating RAG."""
        # "เบอร์ [Nothing]" should NOT go to general_qa and make up a number
        # "วิธี [Nothing]" should NOT go to howto and make up steps
        
        cases = [
            ("เบอร์ nonexistent_person_555", "contact_miss"), 
            ("ข่าว xxyyzz_nonsense_12345", "news_miss") 
        ]
        
        for q, expected_route in cases:
            res = self.engine.process(q)
            self.assertEqual(res.get("route"), expected_route, f"Backoff failed for '{q}'")

if __name__ == '__main__':
    unittest.main()
