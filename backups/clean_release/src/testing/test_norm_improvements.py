
import sys
import os
import unittest
import yaml

sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.utils.normalization import normalize_text, remove_leading_combining_marks

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class NormImprovementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[NormImprovementTest] Initializing ChatEngine...")
        cls.config = load_config("configs/config.yaml")
        if "cache" not in cls.config: cls.config["cache"] = {}
        cls.config["cache"]["enabled"] = False
        cls.engine = ChatEngine(cls.config)

    def test_typo_removal_unit(self):
        print("\n--- Testing Typo Removal (Unit) ---")
        self.assertEqual(remove_leading_combining_marks("๊ u-mux"), "u-mux")
        self.assertEqual(remove_leading_combining_marks(" ๋  test"), "test")
        self.assertEqual(remove_leading_combining_marks("้omc"), "omc")
        
    def test_umux_integration(self):
        # Case: "เบอร์ ๊ u-mux" -> Should Normalize -> Alias -> Contact Hit
        q = "เบอร์ ๊ u-mux"
        print(f"\n--- Testing: {q} ---")
        resp = self.engine.process(q)
        print(f"Route: {resp['route']}")
        print(f"Answer: {resp['answer']}")
        
        self.assertIn("contact_hit", resp['route'])
        self.assertIn("0-2575-7117-8", resp['answer']) # Expected U-MUX phone

    def test_omc_hatyai(self):
        # Case: "เบอร์ OMC หาดใหญ่" -> Should match "ศูนย์ OMC หาดใหญ่"
        # Logic: strip noise "ศูนย์"? Or Alias?
        # If "omc" is aliased to "OMC", and we strip "ศูนย์", it might match "omc หาดใหญ่" vs "ศูนย์ omc หาดใหญ่"
        # Let's see if fuzzy matching works or if we need better alias handling.
        q = "เบอร์ OMC หาดใหญ่"
        print(f"\n--- Testing: {q} ---")
        resp = self.engine.process(q)
        print(f"Route: {resp['route']}")
        
        if "contact_hit" not in resp['route']:
            print("Trying with 'ศูนย์' prefix manually to debug...")
            q2 = "เบอร์ ศูนย์ OMC หาดใหญ่"
            resp2 = self.engine.process(q2)
            print(f"With Prefix Route: {resp2['route']}")
            
        self.assertIn("contact_hit", resp['route'])
        self.assertIn("0-7425-1135", resp['answer']) # Expected OMC Hatyai phone

    def test_ip_network_robustness(self):
         # Regression strict check
         q = "เบอร์หน่วยIP Network"
         print(f"\n--- Testing: {q} ---")
         resp = self.engine.process(q)
         self.assertIn("contact_hit", resp['route'])
         self.assertIn("IP Network", resp['answer'])

if __name__ == "__main__":
    unittest.main()
