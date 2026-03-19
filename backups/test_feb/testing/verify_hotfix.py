
import sys
import os
import unittest
import yaml

# Ensure src is in path
sys.path.append(os.getcwd())

from src.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class HotfixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[HotfixTest] Initializing ChatEngine...")
        cls.config = load_config("configs/config.yaml")
        # Disable cache to allow fresh logic testing
        if "cache" not in cls.config: cls.config["cache"] = {}
        cls.config["cache"]["enabled"] = False
        
        cls.engine = ChatEngine(cls.config)

    def test_team_lookup_helpdesk(self):
        print("\n--- Testing Team Lookup: HelpDesk ---")
        q = "สมาชิกงานงาน HelpDesk (ดูแลลูกค้า"
        resp = self.engine.process(q)
        print(f"Query: {q}")
        print(f"Route: {resp['route']}")
        print(f"Answer: {resp['answer'][:100]}...")
        
        # Expect HIT or AMBIGUOUS (with suggestions including HelpDesk)
        # Should NOT be team_miss
        self.assertNotEqual(resp['route'], 'team_miss')
        self.assertTrue("HelpDesk" in resp['answer'] or "helpdesk" in resp['answer'].lower())

    def test_location_slicing_crash(self):
        print("\n--- Testing Location Slicing Crash ---")
        q = "เบอร์ สื่อสารข้อมูล ระนอง"
        # This was crashing with NameError: slice_markdown_section
        try:
            resp = self.engine.process(q)
            print(f"Query: {q}")
            print(f"Route: {resp['route']}")
            print(f"Answer: {resp['answer'][:100]}...")
            print("✅ No Crash Detected")
        except NameError as e:
            self.fail(f"Crash Detected: {e}")
        except Exception as e:
            print(f"Other Error: {e}")
            # Other errors might happen (e.g. LLM timeout), but NameError must be gone
            if "slice_markdown_section" in str(e):
                self.fail(f"Crash Detected: {e}")

if __name__ == "__main__":
    unittest.main()
