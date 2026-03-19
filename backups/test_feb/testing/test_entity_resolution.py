
import unittest
import json
import re
from unittest.mock import MagicMock
from src.rag.handlers.directory_handler import DirectoryHandler
from src.ai.router import IntentRouter

class TestEntityResolution(unittest.TestCase):
    def test_merge_logic(self):
        """Verify that split records are merged by (Role, Name) key."""
        # Simulated raw positions extracted from different files
        raw_positions = [
            # File 1: Name + Role + Email
            {
                "role": "Manager",
                "name": "John Doe",
                "phones": [],
                "faxes": [],
                "emails": ["john@nt.com"],
                "source": "http://page1"
            },
            # File 2: Name + Role + Phone
            {
                "role": "Manager", 
                "name": "John Doe",
                "phones": ["02-123-4567"], 
                "faxes": [], 
                "emails": [], 
                "source": "http://page2"
            }
        ]
        
        # Re-implement the merge logic here to verify it (White-box testing the logic inserted in script)
        merged = {}
        for p in raw_positions:
            r_key = p["role"].strip()
            n_key = re.sub(r"\s+", "", p["name"]).lower()
            key = (r_key, n_key)
            
            if key not in merged:
                merged[key] = {
                    "role": p["role"],
                    "name": p["name"],
                    "phones": set(p["phones"]),
                    "faxes": set(p["faxes"]),
                    "emails": set(p["emails"]),
                    "sources": {p["source"]}
                }
            else:
                if len(p["name"]) > len(merged[key]["name"]): merged[key]["name"] = p["name"]
                merged[key]["phones"].update(p["phones"])
                merged[key]["faxes"].update(p["faxes"])
                merged[key]["emails"].update(p["emails"])
                merged[key]["sources"].add(p["source"])
                
        # Verification
        self.assertEqual(len(merged), 1)
        entity = list(merged.values())[0]
        self.assertEqual(entity["name"], "John Doe")
        self.assertIn("john@nt.com", entity["emails"])
        self.assertIn("02-123-4567", entity["phones"])
        self.assertEqual(len(entity["sources"]), 2)

    def test_position_handler_fuzzy_lookup(self):
        """Verify DirectoryHandler finds 'ชจญ.ภ.4' correctly."""
        # Mock Index with merged data
        mock_index = {
            "ชจญ.ภ.4": [
                {
                    "role": "ชจญ.ภ.4",
                    "name": "นายสมชาย ใจดี",
                    "phones": ["074-999999"],
                    "emails": ["somchai@nt.com"],
                    "sources": ["http://source1"]
                }
            ],
            "ผจ.สบลตน.": [
                {
                    "role": "ผจ.สบลตน.",
                    "name": "นางสาวสวย จริงใจ",
                    "phones": [],
                    "emails": [],
                    "sources": []
                }
            ]
        }
        
        handler = DirectoryHandler(position_index=mock_index, records=[])
        
        # Case 1: Exact Query
        q1 = "ใครตำแหน่ง ชจญ.ภ.4"
        res1 = handler.handle_position_holder(q1)
        self.assertEqual(res1["route"], "position_holder_hit")
        self.assertIn("นายสมชาย ใจดี", res1["answer"])
        self.assertIn("074-999999", res1["answer"])
        
        # Case 2: No match (Fuzzy fail for now, but ensure structure)
        q2 = "ใครตำแหน่ง ประธานาธิบดี"
        res2 = handler.handle_position_holder(q2)
        self.assertEqual(res2["route"], "position_miss")

    def test_router_intent(self):
        """Verify Router picks up 'ใครตำแหน่ง'."""
        router = IntentRouter(llm_config={})
        q = "ใครตำแหน่ง ชจญ.ภ.4"
        res = router.route(q)
        self.assertEqual(res["intent"], "POSITION_HOLDER_LOOKUP")
        
    def test_regression_routing(self):
        """Regression tests for Priority (Phase 49 Fix)."""
        router = IntentRouter(llm_config={})
        
        # Case 1: "ใครตำแหน่ง ผส." -> POSITION_HOLDER_LOOKUP (NOT Management)
        # Even though "ผส." is a management keyword, "ใครตำแหน่ง" must take precedence.
        q1 = "ใครตำแหน่ง ผส.บลตน."
        res1 = router.route(q1)
        self.assertEqual(res1["intent"], "POSITION_HOLDER_LOOKUP")
        
        # Case 2: "รายชื่อผู้บริหาร" -> MANAGEMENT_LOOKUP (Standard)
        q2 = "รายชื่อผู้บริหาร"
        res2 = router.route(q2)
        self.assertEqual(res2["intent"], "MANAGEMENT_LOOKUP")
        
        # Case 3: "ผส.บลตน." (Just Role) -> MANAGEMENT_LOOKUP (or Person Lookup via DirectoryHandler)
        q3 = "ผส.บลตน."
        res3 = router.route(q3)
        self.assertEqual(res3["intent"], "MANAGEMENT_LOOKUP")
        
        # Case 4: Typo "ครตำแหน่ง ผส.บลตน." -> POSITION_HOLDER_LOOKUP
        q4 = "ครตำแหน่ง ผส.บลตน."
        res4 = router.route(q4)
        self.assertEqual(res4["intent"], "POSITION_HOLDER_LOOKUP")

    def test_directory_stripping(self):
        """Test extraction of role from query string."""
        handler = DirectoryHandler(position_index={}, records=[])
        
        # We need to expose internal logic or just check if it routes to 'position_miss' with correct key in message if we mock _find_matches?
        # Let's trust the integration test logic.
        
        # Mocking _find_matches to return empty so we see the Fallback message?
        # Or better, check the q_clean logic by invoking specialized method that calls it?
        # Actually handle_position_holder calls _find_matches(q_norm).
        
        # Let's subclass to spy
        class SpyHandler(DirectoryHandler):
            def _find_matches(self, query):
                self.last_query = query
                return []
                
        spy = SpyHandler({}, [])
        
        # "ใครตำแหน่ง ผส.บลตน." -> Should search for "ผส.บลตน."
        spy.handle_position_holder("ใครตำแหน่ง ผส.บลตน.")
        print(f"Spy Query 1: {spy.last_query}")
        self.assertTrue("ผส" in spy.last_query)
        self.assertFalse("ใ" in spy.last_query) # Should NOT have "ใ" leftover
        
        # "ครตำแหน่ง ผส.บลตน." -> Should also strip "ครตำแหน่ง"
        spy.handle_position_holder("ครตำแหน่ง ผส.บลตน.")
        print(f"Spy Query 2: {spy.last_query}")
        self.assertTrue("ผส" in spy.last_query)
        self.assertFalse("คร" in spy.last_query) # Should be stripped

if __name__ == '__main__':
    unittest.main()
