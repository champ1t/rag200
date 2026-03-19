
import unittest
from src.ai.router import IntentRouter

class TestRouterRefinement(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_contact_false_positive(self):
        # Problem: "แก้ user สำหรับลูกค้า context private" routes to CONTACT_LOOKUP
        # Likely due to "ext" in "context" or broad matching.
        q = "แก้ user สำหรับลูกค้า context private"
        res = self.router.route(q)
        print(f"Query: '{q}' -> Intent: {res['intent']} (Reason: {res.get('reason')})")
        
        # Expectation: SHOULD BE HOWTO or GENERAL_QA
        self.assertNotEqual(res['intent'], "CONTACT_LOOKUP", "Should not route to CONTACT_LOOKUP")
        self.assertIn(res['intent'], ["HOWTO_PROCEDURE", "GENERAL_QA"])

    def test_news_link_filtering(self):
        # This requires mocking ChatEngine or testing the logic in isolation.
        # Since I can't easily mock ChatEngine here without dependencies, 
        # I rely on code inspection and will write a unit test for the FILTER LOGIC 
        # if I extract it, or just verify Router intent for "ข่าวสาร" first.
        
        q = "ข่าวสารSMC"
        res = self.router.route(q)
        self.assertEqual(res['intent'], "NEWS_SEARCH")
        
if __name__ == "__main__":
    unittest.main()
