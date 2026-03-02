
import unittest
import sys
import os

sys.path.append(os.getcwd())
try:
    from src.ai.router import IntentRouter
except ImportError:
    pass

class TestContactRouting(unittest.TestCase):
    def test_ambiguous_contact_queries(self):
        print("\n--- Test: Ambiguous Contact Queries ---")
        router = IntentRouter()
        
        # 1. Valid Person Lookup
        q1 = "ขอเบอร์คุณสมชาย"
        res1 = router.route(q1)
        print(f"Query: '{q1}' -> {res1['intent']}")
        self.assertEqual(res1['intent'], "PERSON_LOOKUP")
        
        # 2. Procedure involving 'Phone' (False Positive Candidate)
        q2 = "โอนสายโทรศัพท์"
        res2 = router.route(q2)
        print(f"Query: '{q2}' -> {res2['intent']}")
        # Should NOT be PERSON_LOOKUP (Ideally HOWTO or GENERAL)
        
        # 3. Procedure "Contact Method"
        q3 = "วิธีติดต่อ Admin"
        res3 = router.route(q3)
        print(f"Query: '{q3}' -> {res3['intent']}")
        # Should be HOWTO (or Person? "Method to contact" -> Person info?)
        # "วิธี" usually implies procedure.
        
        # 4. Explicit "Call" (Could be person?)
        q4 = "โทรหาประชาสัมพันธ์"
        res4 = router.route(q4)
        print(f"Query: '{q4}' -> {res4['intent']}")
        self.assertEqual(res4['intent'], "PERSON_LOOKUP")

if __name__ == "__main__":
    unittest.main()
