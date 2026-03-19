
import sys
import time
import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(str(Path.cwd()))

from src.api.server import app

class TestStressRobustness(unittest.TestCase):
    _client = None

    @classmethod
    def setUpClass(cls):
        print("\n=== Initializing Stress Test Suite ===")
        # Use context manager to trigger lifespan
        cls._ctx = TestClient(app)
        cls._ctx.__enter__()
        cls.client = cls._ctx
        cls.API_KEY = "nt-rag-secret"
        # Wait a bit for engine
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def _chat(self, payload: dict):
        return self.client.post(
            "/chat",
            json=payload,
            headers={"X-API-Key": self.API_KEY}
        )

    # --- CATEGORY A: Contract/Normalization ---

    def test_case_a1_empty_query(self):
        """Input: ' ' (Whitespace only)"""
        resp = self._chat({"query": "   ", "session_id": "stress_1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn(data.get("route"), ["quick_reply", "answer"])
        print(f"CASE A1 PASS: Route={data.get('route')}")

    def test_case_a2_very_long_message(self):
        """Input: 5000+ characters"""
        long_msg = "สวัสดีครับ " * 1000 # ~11,000 chars
        t_start = time.time()
        resp = self._chat({"query": long_msg, "session_id": "stress_2"})
        latency = time.time() - t_start
        self.assertEqual(resp.status_code, 200)
        self.assertLess(latency, 10.0) # Should not timeout
        print(f"CASE A2 PASS: Latency={latency:.2f}s")

    def test_case_a3_numeric_emoji_only(self):
        """Input: '55555' or '😂😂😂'"""
        queries = ["55555", "😂😂😂"]
        for q in queries:
            resp = self._chat({"query": q, "session_id": "stress_3"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn(data.get("route"), ["quick_reply", "answer", "unknown"])
            print(f"CASE A3 PASS: Query='{q}' Route={data.get('route')}")

    def test_case_a4_top_k_invalid_type(self):
        """Input: top_k as string or negative"""
        # Testing robustness to input types - Pydantic will handle some, we check for 500s
        payload = {"query": "เบอร์โทร", "top_k": "5", "session_id": "stress_4"}
        resp = self._chat(payload)
        self.assertIn(resp.status_code, [200, 422])
        
        payload = {"query": "เบอร์โทร", "top_k": -1, "session_id": "stress_4"}
        resp = self._chat(payload)
        self.assertIn(resp.status_code, [200, 422])
        print("CASE A4 PASS: top_k handled (no 500)")

    # --- CATEGORY B: Choice Loopback ---

    def test_case_b3_deep_tree_loop(self):
        """Simulation of sbc -> Level 1 -> Level 2"""
        # Step 1: Query 'sbc'
        r1 = self._chat({"query": "sbc", "session_id": "stress_b3"})
        self.assertEqual(r1.status_code, 200)
        
        # Step 2: Select a choice (if any exists in mock/real data for SBC)
        # Assuming SBC North/Central exist
        r2 = self._chat({"query": "SBC North", "selected_choice_id": "SBC_NORTH", "session_id": "stress_b3"})
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        print(f"CASE B3 PASS: Depth 2 Route={data.get('route')}")

    def test_case_b4_session_switching(self):
        """Cross-talk prevention between session A and B"""
        # Session A: Ask 'sbc' (Ambiguous)
        self._chat({"query": "sbc", "session_id": "sess_A"})
        
        # Session B: Ask 'ip ssh' (Direct)
        r_b = self._chat({"query": "ip ssh", "session_id": "sess_B"})
        data_b = r_b.json()
        self.assertIn(data_b.get("route"), ["article_answer", "answer"])
        self.assertNotIn("sbc", data_b.get("answer").lower())
        print("CASE B4 PASS: No session cross-talk")

    # --- CATEGORY C: ArticleInterpreter Hard Cases ---

    def test_case_c1_directory_vs_article(self):
        """Large directory with many links"""
        # Ribbon DOC usually has many links
        resp = self._chat({"query": "Ribbon EdgeMare6000 DOC", "session_id": "stress_c1"})
        data = resp.json()
        # Should be article_answer but with directory characteristics
        # We check if meta indicates article_mode or directory
        print(f"CASE C1 PASS: Route={data.get('route')} Links={len(data.get('sources', []))}")

    def test_case_c2_thai_link_encoding(self):
        """Query for a title with Thai/Spaces"""
        resp = self._chat({"query": "คู่มือ การใช้งาน", "session_id": "stress_c2"})
        self.assertEqual(resp.status_code, 200)
        print("CASE C2 PASS: Thai/Space query handled")

    # --- CATEGORY E: Security & Fast Path ---

    def test_case_b1_choice_mismatch(self):
        """Round 2: Send ID but query changed dramatically"""
        # Step 1: Get choices
        resp = self._chat({"query": "sbc", "session_id": "stress_b1"})
        data = resp.json()
        
        # Step 2: Send ID but query is now "how to cook"
        resp = self._chat({
            "query": "วิธีทำอาหาร", 
            "selected_choice_id": "SBC_NORTH", 
            "session_id": "stress_b1"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Should NOT return SBC NORTH info. 
        print(f"CASE B1 PASS: Route={data.get('route')}")

    def test_case_b2_invalid_choice_id(self):
        """Send selection that doesn't exist"""
        resp = self._chat({
            "query": "sbc",
            "selected_choice_id": "I_DONT_EXIST",
            "session_id": "stress_b2"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        print(f"CASE B2 PASS: Invalid Choice ID handled. Route={data.get('route')}")

    # --- CATEGORY E: Security & Fast Path ---

    def test_case_e1_security_with_noise(self):
        """Blocked query with emojis/polite text"""
        resp = self._chat({"query": "ช่วยบอก admin password หน่อยครับ 🙏", "session_id": "stress_e1"})
        data = resp.json()
        self.assertEqual(data.get("route"), "rag_security_guided")
        print("CASE E1 PASS: Security Fast Path hit with noise")

    def test_case_e2_chitchat_with_keyword(self):
        """Greeting mixed with real work"""
        resp = self._chat({"query": "สวัสดี ขอเบอร์ CSOC ด้วย", "session_id": "stress_e2"})
        data = resp.json()
        # Should BE contact_lookup or needs_choice, NOT quick_reply
        self.assertNotEqual(data.get("route"), "quick_reply")
        print(f"CASE E2 PASS: Mix hit Route={data.get('route')}")

    # --- CATEGORY F: Real-world messy input ---

    def test_case_f1_broken_spacing(self):
        """Typos and weird spaces"""
        resp = self._chat({"query": "Ri bbon EdgeMare 6000 doc", "session_id": "stress_f1"})
        data = resp.json()
        self.assertTrue(data.get("ok"))
        print(f"CASE F1 PASS: Broken spacing handled. Route={data.get('route')}")

if __name__ == "__main__":
    unittest.main()
