import sys
import os
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

class TestDeterministicRetrieval(unittest.TestCase):
    def setUp(self):
        self.cache = ProcessedCache("data/processed")
        # Mock load to populate index manuall
        self.cache._loaded = True
        self.cache._link_index = {
            # Expected Target Titles (Normalized Keys -> List of Entries)
            "uaps zte master slave": [{"text": "zte uaps - master slave ไม่สลับกลับ", "href": "url1"}],
            "basic command olt zte c300": [{"text": "BASIC COMMAND OLT ZTE C300", "href": "url2"}],
            "huawei ne8000 command": [{"text": "Huawei NE8000 Command Manual", "href": "url3"}],
            "full list of olt commands": [{"text": "Full List of OLT Commands", "href": "url4"}],
            "zte update command fttx": [{"text": "ZTE update คำสั่ง FTTx", "href": "url5"}],
            "cisco asr920 config": [{"text": "Config Cisco ASR920", "href": "url6"}]
        }
        # We need to ensure keys are normalized as expected by find_links logic?
        # Actually find_best_article_match iterates _link_index items.
        # But keys in _link_index are usually normalized.
        # Let's populate with normalized keys based on `normalize_key` method logic (simple lower)
        # But `find_best_article_match` iterates values, so keys don't strictly matter for iteration 
        # unless we fail to iterate.
        pass

    def test_title_fidelity(self):
        """Test 1: Query tokens subset of Title tokens (High Confidence)"""
        # "BASIC COMMAND OLT ZTE C300" -> "BASIC COMMAND OLT ZTE C300"
        match = self.cache.find_best_article_match("BASIC COMMAND OLT ZTE C300")
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], "BASIC COMMAND OLT ZTE C300")
        self.assertGreaterEqual(match["score"], 0.95)

        # "ZTE update คำสั่ง FTTx" -> "ZTE update คำสั่ง FTTx"
        match = self.cache.find_best_article_match("ZTE update คำสั่ง FTTx")
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], "ZTE update คำสั่ง FTTx")

    def test_alias_robustness(self):
        """Test 2: Alias Mapping (ne8000 -> huawei ne8000)"""
        # "ne8000 command" -> Should match "Huawei NE8000 Command Manual" via Alias
        match = self.cache.find_best_article_match("ne8000 command")
        self.assertIsNotNone(match)
        self.assertIn("Huawei NE8000", match["title"])
        self.assertGreaterEqual(match["score"], 0.9)

        # "uaps zte" -> Should match "zte uaps - master slave" via Alias or Keyword
        match = self.cache.find_best_article_match("uaps zte")
        self.assertIsNotNone(match)
        self.assertIn("zte uaps", match["title"])

    def test_noise_tolerance(self):
        """Test 3: Noise Word Removal (วิธี, config, command)"""
        # "วิธี config zte olt c300" -> "BASIC COMMAND OLT ZTE C300"
        # Noise: "วิธี", "config" removed.
        # Remaining: "zte olt c300" -> Subset of "BASIC COMMAND OLT ZTE C300"
        match = self.cache.find_best_article_match("วิธี config zte olt c300")
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], "BASIC COMMAND OLT ZTE C300")
        
        # "ขอ command asr920" -> "Config Cisco ASR920"
        # Noise: "ขอ" (not in list but maybe ignore?), "command"
        # Alias: "asr920" -> "cisco asr920"
        # Target: "Config Cisco ASR920" (Clean: cisco asr920)
        match = self.cache.find_best_article_match("ขอ command asr920")
        self.assertIsNotNone(match)
        self.assertIn("ASR920", match["title"])

if __name__ == "__main__":
    unittest.main()
