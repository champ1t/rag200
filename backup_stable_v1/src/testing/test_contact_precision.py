
import unittest
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd()))

from src.chat_engine import ChatEngine
from src.rag.handlers.contact_handler import ContactHandler

class TestContactPrecision(unittest.TestCase):
    def setUp(self):
        # Initializing Engine (Mock or Real)
        config_path = Path("configs/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self.cfg = yaml.safe_load(f)
        else:
            self.cfg = {}
            
        self.engine = ChatEngine(self.cfg)
        self.records = self.engine.records # Access loaded records

    def test_location_filtering(self):
        query = "เบอร์ศูนย์ OMC หาดใหญ่"
        print(f"\n[TEST] Query: {query}")
        
        # 1. Direct Handler Check
        res = ContactHandler.handle(query, self.records, self.engine.directory_handler)
        hits = res.get("hits", [])
        
        print(f"[TEST] Hits Found: {len(hits)}")
        for h in hits:
            name = h.get("name", "")
            role = h.get("role", "")
            print(f" - {name} ({role})")
            
        # Assertion: Should contain "หาดใหญ่" but NOT "พุนพิน"
        has_hatyai = any("หาดใหญ่" in (h.get("name","")+str(h.get("role",""))) for h in hits)
        has_phunphin = any("พุนพิน" in (h.get("name","")+str(h.get("role",""))) for h in hits)
        
        self.assertTrue(has_hatyai, "Result should contain Hat Yai")
        self.assertFalse(has_phunphin, "Result should NOT contain Phunphin (Precision Filter)")
        
if __name__ == "__main__":
    unittest.main()
