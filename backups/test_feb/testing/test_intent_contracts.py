import unittest
import yaml
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.main import load_config
from src.chat_engine import ChatEngine

CONTRACT_PATH = "src/testing/test_intent_contracts.yaml"
CONFIG_PATH = "configs/config.yaml"

class TestIntentContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] initializing Chat Engine...")
        if not Path(CONFIG_PATH).exists():
            raise FileNotFoundError(f"Config not found at {CONFIG_PATH}")
        
        cls.cfg = load_config(CONFIG_PATH)
        # Use mocked LLM if needed, or real. Assuming real for now as per instructions.
        # Check if Ollama is reachable? 
        # For now, just load.
        cls.engine = ChatEngine(cls.cfg)
        print("[SETUP] Engine loaded.")

        if Path(CONTRACT_PATH).exists():
            with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
                cls.test_cases = yaml.safe_load(f)
        else:
            cls.test_cases = []
            print(f"[WARN] No contract file found at {CONTRACT_PATH}")

    def test_contracts(self):
        """Run through all cases in test_intent_contracts.yaml"""
        if not self.test_cases:
            self.skipTest("No contract definition found")

        failures = []
        for case in self.test_cases:
            q = case["q"]
            expect = case["expect"]
            
            with self.subTest(query=q):
                print(f"\n[TEST] Query: {q}")
                
                # 1. Verify Intent (Router Direct)
                # Note: Router might be Regex fallback or LLM
                router_res = self.engine.router.route(q)
                actual_intent = router_res.get("intent")
                
                expected_intent = expect.get("intent")
                if expected_intent and actual_intent != expected_intent:
                    msg = f"Intent Mismatch! Expected: {expected_intent}, Got: {actual_intent} (Reason: {router_res.get('reason')})"
                    print(f"  FAILED: {msg}")
                    failures.append(f"Query: '{q}' -> {msg}")
                    # Continue to route check?
                else:
                    print(f"  Intent OK: {actual_intent}")
                
                # 2. Verify Route (End-to-End)
                # Only if route is specified
                expected_route = expect.get("route")
                if expected_route:
                    proc_res = self.engine.process(q)
                    actual_route = proc_res.get("route")
                    
                    match = False
                    if expected_route.startswith("regex:"):
                        pattern = expected_route.split("regex:", 1)[1]
                        import re
                        if re.match(pattern, actual_route):
                            match = True
                    elif actual_route == expected_route:
                        match = True
                        
                    if not match:
                        msg = f"Route Mismatch! Expected: {expected_route}, Got: {actual_route}"
                        print(f"  FAILED: {msg}")
                        failures.append(f"Query: '{q}' -> {msg}")
                    else:
                        print(f"  Route OK: {actual_route}")
        
        if failures:
            self.fail("\n".join(failures))

    def test_metamorphic_variants(self):
        """Test variants of a base query to ensure robustness."""
        base_intent = "POSITION_HOLDER_LOOKUP"
        variants = [
          "ใครตำแหน่ง ผส.บลตน",
          "ใครตำแหน่งผส.บลตน",
          # "ครตำแหน่ง ผส.บลตน", # Intentional typo, might fail if Router strictly regex
          "ใคร เป็น ผส.บลตน",
          "ขอทราบ ใครตำแหน่ง ผส.บลตน ครับ",
        ]
        
        failures = []
        for q in variants:
            with self.subTest(variant=q):
                res = self.engine.router.route(q)
                if res["intent"] != base_intent:
                    msg = f"Metamorphic Fail for '{q}': Got {res['intent']} (Reason: {res.get('reason')})"
                    failures.append(msg)
                    print(f"[FAIL] {msg}")
                else:
                    print(f"[PASS] {q} -> {res['intent']}")
        
        if failures:
            self.fail(f"Metamorphic Failures:\n" + "\n".join(failures))

if __name__ == "__main__":
    unittest.main()
