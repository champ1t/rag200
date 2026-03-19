
import sys
import os
import unittest
import yaml

sys.path.append(os.getcwd())

from src.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class SMCTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SMCTest] Initializing ChatEngine...")
        cls.config = load_config("configs/config.yaml")
        if "cache" not in cls.config: cls.config["cache"] = {}
        cls.config["cache"]["enabled"] = False # Disable cache
        cls.engine = ChatEngine(cls.config)

    def test_captain(self):
        q = "เบอร์คุณกับตัน SMC"
        print(f"\n--- Testing: {q} ---")
        resp = self.engine.process(q)
        print(f"Route: {resp['route']}")
        print(f"Answer: {resp['answer']}")
        
        # Verify
        self.assertIn("092-992-9459", resp['answer'])
        # It might match "นายกัปตัน (Captain)" with "กับตัน" via fuzzy or normalized
    
    def test_karn(self):
        q = "เบอร์คุณก้าน SMC"
        print(f"\n--- Testing: {q} ---")
        resp = self.engine.process(q)
        print(f"Route: {resp['route']}")
        print(f"Answer: {resp['answer']}")
        
        self.assertIn("084-468-9122", resp['answer'])

    def test_bom(self):
        q = "เบอร์คุณบอม SMC"
        print(f"\n--- Testing: {q} ---")
        resp = self.engine.process(q)
        print(f"Route: {resp['route']}")
        print(f"Answer: {resp['answer']}")
        
        self.assertIn("061-783-6661", resp['answer'])

if __name__ == "__main__":
    unittest.main()
