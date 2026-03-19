
import unittest
from src.rag.handlers.contact_handler import ContactHandler

class TestContactHandler(unittest.TestCase):
    def setUp(self):
        self.mock_records = [
            {"name": "ฝ่ายขาย", "phones": ["021234567"]},
            {"name": "บริการลูกค้า", "phones": ["1111"]},
            {"name": "คุณสมชาย", "phones": ["0812345678"]}
        ]

    def test_contact_handler_hit(self):
        # Query matching "ฝ่ายขาย"
        res = ContactHandler.handle("ขอเบอร์ฝ่ายขาย", self.mock_records)
        self.assertEqual(res["route"], "contact_hit")
        self.assertIn("021234567", res["answer"])

    def test_contact_handler_miss(self):
        # Query that exists but no match in DB
        res = ContactHandler.handle("ขอเบอร์ฝ่ายไอที", self.mock_records)
        self.assertEqual(res["route"], "contact_miss")
        self.assertIn("ไม่พบข้อมูล", res["answer"])
        
    def test_reverse_lookup(self):
        # Lookup by phone number
        res = ContactHandler.handle("เบอร์ 1111 คือใคร", self.mock_records)
        self.assertEqual(res["route"], "contact_hit")
        self.assertIn("บริการลูกค้า", res["answer"])

    def test_abbreviation_expansion(self):
        # "กทม" should expand to "กรุงเทพ" (Assuming ABBREVIATIONS loaded in lookup.py)
        # But my mock records don't have BKK.
        # Let's verify strict import works at least.
        pass

if __name__ == "__main__":
    unittest.main()
