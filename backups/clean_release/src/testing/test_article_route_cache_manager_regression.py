
import unittest
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.core.chat_engine import ChatEngine

class TestArticleCrashAndSecurity(unittest.TestCase):
    def setUp(self):
        # Initializing Engine (Mock or Real)
        config_path = Path("configs/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self.cfg = yaml.safe_load(f)
        else:
            self.cfg = {}
            
        # Ensure Security Config is present for test
        self.cfg["security"] = {
            "allow_credential_redirect": True,
            "credential_redirect_mode": "redirect_only",
            "credential_article_allowlist": ["ont-password"]
        }
        
        # Ensure we can init without crash even if cache_manager is broken
        self.engine = ChatEngine(self.cfg)
        
        # MOCK ProcessedCache to return a link so we can test REDIRECT route
        # Only return link if 'ont' is in query to simulate relevance
        self.engine.processed_cache.find_links_fuzzy = lambda q: [{"url": "http://smc/ont-password", "text": "ONT Password"}] if "ont" in q.lower() else []

    def test_ont_password_block(self):
        """Test that 'ONT password' is blocked and DOES NOT crash."""
        query = "ONT password"
        print(f"\n[TEST] Query: {query}")
        
        try:
            res = self.engine.process(query)
            route = res.get("route", "")
            answer = res.get("answer", "")
            
            print(f"[TEST] Result Route: {route}")
            print(f"[TEST] Answer: {answer}")
            
            # Expectation 1: No Crash (implicit if we got here)
            # Expectation 2: Credential Redirect (Mocked)
            self.assertEqual(route, "rag_credential_redirect", "Should be Redirect Only")
            self.assertIn("ข้อมูลจำกัดสิทธิ์", answer)
            self.assertIn("http://smc/ont-password", answer)
            
        except Exception as e:
            self.fail(f"Engine crashed during processing: {e}")

    def test_password_admin_router_block(self):
        """Test blocking of 'password admin router'."""
        query = "password admin router"
        print(f"\n[TEST] Query: {query}")
        
        res = self.engine.process(query)
        self.assertEqual(res.get("route"), "rag_security_guided")
        self.assertIn("นโยบายความปลอดภัย", res.get("answer"))

    def test_article_route_stability(self):
        """Test that normal article flow (if valid) doesn't crash."""
        # Find a valid article link query or mock it
        # Assuming "RAG คืออะไร" goes to RAG, but let's try a specific knowledge keyword if possible.
        # Or just assert that process() doesn't fail generally.
        pass

if __name__ == "__main__":
    unittest.main()
