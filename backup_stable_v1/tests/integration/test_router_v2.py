
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())
try:
    from src.chat_engine import ChatEngine
    from src.ai.router import IntentRouter
except ImportError:
    pass

CONFIG = {
    "model": "mock",
    "base_url": "mock",
    "retrieval": {"top_k": 1, "score_threshold": 0.5},
    "llm": {"model": "mock", "base_url": "mock"},
    "chat": {"save_log": False},
    "knowledge_pack": {"enabled": False},
    "cache": {"enabled": False}
}

class TestRouterV2(unittest.TestCase):
    def setUp(self):
        self.engine = ChatEngine(CONFIG)
        self.engine.warmup()
        # Mock Data
        self.engine.records = [
            {"name": "HelpDesk", "name_norm": "helpdesk", "type": "team", "phones": ["1234"], "emails": ["hd@test.com"]},
            {"name": "สมชาย", "name_norm": "สมชาย", "type": "person", "phones": ["9999"], "emails": []}
        ]
        self.engine.position_index = {
            "HelpDesk": [{"role": "HelpDesk", "name": "นาย A", "source": "test"}],
            "ผส.บลตน.": [{"role": "ผส.บลตน.", "name": "ผอ.ใจดี", "source": "test"}]
        }
        self.engine.processed_cache = MagicMock()
        self.engine.processed_cache.find_links_fuzzy.return_value = [
            {"score": 1.0, "items": [{"text": "Doc1", "href": "http://doc1", "source": "s1"}]}
        ]

    # --- Test Cases (A/B/C) ---

    def test_case_1_person_lookup(self):
        # 1) "สมาชิกงาน HelpDesk" -> PERSON_LOOKUP -> position_lookup -> มีรายชื่อ
        q = "สมาชิกงาน HelpDesk"
        res = self.engine.process(q)
        print(f"\nCase 1: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "position_lookup")
        self.assertIn("นาย A", res['answer'])

    def test_case_2_contact_lookup(self):
        # 2) "เบอร์ติดต่องาน HelpDesk" -> CONTACT_LOOKUP -> มีเบอร์ (ห้ามตอบรายชื่ออย่างเดียว)
        q = "เบอร์ติดต่องาน HelpDesk"
        res = self.engine.process(q)
        print(f"\nCase 2: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "contact_lookup")
        self.assertIn("1234", res['answer'])
        
    def test_case_3_status_check(self):
        # 3) "สถานะการใช้งาน FTTxSM ภ.4" -> STATUS_CHECK (ห้ามเข้า position_lookup)
        q = "สถานะการใช้งาน FTTxSM ภ.4"
        res = self.engine.process(q)
        print(f"\nCase 3: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "status_check_mock")
        self.assertIn("ไม่พบข้อมูลสถานะ", res['answer'])

    def test_case_4_howto_log(self):
        # 4) "ตรวจสอบ ONU event log" -> STATUS_CHECK (or HOWTO) (ห้ามเข้า position_lookup)
        # "ตรวจสอบ" -> STATUS_CHECK in V2 taxonomy
        q = "ตรวจสอบ ONU event log"
        res = self.engine.process(q)
        print(f"\nCase 4: '{q}' -> {res['route']}")
        self.assertIn(res['route'], ["status_check_mock", "rag_no_docs", "cache_hit"]) 
        # If mock status, it returns status_check_mock. 
        # Note: "ตรวจสอบ" is matched as STATUS in V2.

    def test_case_5_howto_setting(self):
        # 5) "TR069 CWMP Setting" -> HOWTO_PROCEDURE (Vector Search)
        q = "TR069 CWMP Setting"
        res = self.engine.process(q)
        print(f"\nCase 5: '{q}' -> {res['route']}")
        # Should NOT be position_lookup
        self.assertNotEqual(res['route'], "position_lookup")
        # Should be RAG related
        self.assertIn(res['route'], ["rag_no_docs", "rag_low_score", "rag_answer"])

    def test_case_6_who_is_role(self):
        # 6) "ใครคือ ผส.บลตน." -> PERSON_LOOKUP -> position_lookup
        q = "ใครคือ ผส.บลตน."
        res = self.engine.process(q)
        print(f"\nCase 6: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "position_lookup")
        self.assertIn("ผอ.ใจดี", res['answer'])

    # --- Extra Regression Cases ---

    def test_case_7_contact_miss_fail(self):
        # Intent: CONTACT, but no data -> contact_miss (don't fallback to unknown person)
        q = "ขอเบอร์ Superman"
        res = self.engine.process(q)
        print(f"\nCase 7: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "contact_miss")

    def test_case_8_ambiguous_transfer(self):
        # "วิธีโอนสาย" -> Should be HOWTO, not Contact/Person
        q = "วิธีโอนสายโทรศัพท์"
        res = self.engine.process(q)
        print(f"\nCase 8: '{q}' -> {res['route']}")
        self.assertNotEqual(res['route'], "contact_lookup")
        self.assertNotEqual(res['route'], "position_lookup")

    def test_case_9_reference_link(self):
        # "ขอลิงก์ e-doc"
        q = "ขอลิงก์ e-doc"
        res = self.engine.process(q)
        print(f"\nCase 9: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "link_lookup")

    def test_case_10_status_outage(self):
        # "เน็ตล่มไหม" -> STATUS_CHECK
        q = "เน็ตล่มไหม"
        res = self.engine.process(q)
        print(f"\nCase 10: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "status_check_mock")

    def test_case_11_general_qa(self):
        # "แมวสีอะไร" -> GENERAL -> RAG
        q = "แมวสีอะไร"
        res = self.engine.process(q)
        print(f"\nCase 11: '{q}' -> {res['route']}")
        self.assertIn(res['route'], ["rag_no_docs", "rag_low_score"])

    def test_case_12_mixed_contact_person(self):
        # "ขอเบอร์สมาชิกทีม HelpDesk" -> CONTACT wins Over Person
        q = "ขอเบอร์สมาชิกทีม HelpDesk"
        res = self.engine.process(q)
        print(f"\nCase 12: '{q}' -> {res['route']}")
        self.assertEqual(res['route'], "contact_lookup")
        
    def test_case_13_whitespace_mismatch(self):
        """
        Q: "เบอร์ ServiceCenter" (No Space) -> Should match "Service Center" (Space) record.
        """
        # Add mock record
        self.engine.records.append({
            "name": "Service Center", "name_norm": "service center", 
            "type": "team", "phones": ["5555"]
        })
        
        q = "เบอร์ ServiceCenter" 
        res = self.engine.process(q)
        self.assertEqual(res['route'], "contact_lookup")
        self.assertIn("5555", res['answer'])

    def test_case_14_lowercase_mismatch(self):
        """
        Q: "สมาชิก help desk" -> Matches "HelpDesk" role (Part B Match).
        """
        # Mock position index has "HelpDesk" -> [{"role": "HelpDesk", "name": "นาย A"}]
        q = "สมาชิก help desk"
        res = self.engine.process(q)
        self.assertEqual(res['route'], "position_lookup")
        self.assertIn("นาย A", res['answer'])

    def test_case_15_hybrid_join(self):
        """
        Q: "สมาชิก help desk" -> matches "HelpDesk" role (no phones).
        Hybrid Join -> Finds "Mr. Hybrid" in records (with phones).
        """
        # 1. Position Index has Role but NO phones
        self.engine.position_index["HelpDesk"] = [{"role": "HelpDesk", "name": "Mr. Hybrid", "phones": []}]
        
        # 2. Main Records has Person with SAME name AND phones
        self.engine.records.append({
            "name": "Mr. Hybrid", "name_norm": "mr hybrid", "type": "person", 
            "phones": ["081-HYBRID"], "emails": []
        })
        
        q = "สมาชิก help desk"
        res = self.engine.process(q)
        
        self.assertEqual(res['route'], "position_lookup")
        # Must find the name
        self.assertIn("Mr. Hybrid", res['answer'])
        # Must find the phone (from Hybrid Join)
        self.assertIn("081-HYBRID", res['answer'])

if __name__ == "__main__":
    unittest.main()
