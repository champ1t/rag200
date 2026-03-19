import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.chat_engine import ProcessedCache, ChatEngine

class TestFuzzyLink(unittest.TestCase):
    def setUp(self):
        # Mock config
        self.cfg = {
            "retrieval": {"top_k": 3},
            "llm": {"model": "mock", "base_url": "mock"},
            "chat": {"show_context": False, "save_log": False}
        }
        # Initialize engine (will load real data if present)
        self.engine = ChatEngine(self.cfg)
        
    def test_normalization(self):
        pc = self.engine.processed_cache
        self.assertEqual(pc.normalize_key("Mac-Address"), "mac address")
        self.assertEqual(pc.normalize_key("  Link   AAA  "), "link aaa")
        self.assertEqual(pc.normalize_key("Wi-Fi Access"), "wi fi access")
        
    def test_fuzzy_match(self):
        # Assuming "mac address search" exists or similar
        # Let's test against known link anchors if possible.
        # "ระบบบันทึกงาน SMC" -> "smc" (substring fallback)
        # "Mac Address Finding" -> "mac address finding" (fuzzy to "mac address finding" or close?)
        
        # Test 1: Typos
        # e.g. "edoccument" -> "edocument" (if exists)
        # We need to know what's in the index.
        # Let's check a few known keys
        keys = self.engine.processed_cache._keys
        print(f"Total keys: {len(keys)}")
        if not keys:
            print("No keys loaded, skipping fuzzy test.")
            return

        # Pick a key to test typo
        target = keys[0]
        # Create typo: swap chars or add char
        typo_query = target + "x" 
        
        res = self.engine.processed_cache.find_links_fuzzy(typo_query, threshold=0.8)
        self.assertTrue(len(res) > 0, f"Should find {target} with query {typo_query}")
        self.assertEqual(res[0]['key'], target)
        
    def test_routing_alias(self):
        # Test alias "wifi" -> "wireless"
        # Only works if "wireless" is in the index or matched via fuzzy
        # Assuming there is a link containing "wireless" in the real data?
        pass

if __name__ == "__main__":
    unittest.main()
