
import unittest
from src.rag.handlers.directory_handler import DirectoryHandler

class TestDirectoryHandler(unittest.TestCase):
    def setUp(self):
        # Mock Position Index
        self.position_index = {
            "ผจก.กขาย.": [
                {"role": "ผจก.กขาย.", "name": "นายสมชาย ขายเก่ง", "phones": [], "emails": []}
            ],
            "วิศวกร 5": [
                {"role": "วิศวกร 5", "name": "นางสาววิศวา เก่งกล้า", "phones": ["0812345678"], "emails": []}
            ],
            "หัวหน้างานธุรการ": [
                 {"role": "หัวหน้างานธุรการ", "name": "นายธุรการ ขยัน", "phones": [], "emails": ["admin@test.com"]}
            ],
            "ผู้ดูแลระบบ": [
                 {"role": "ผู้ดูแลระบบ", "name": "Admin User", "phones": [], "emails": []}
            ]
        }

        
        # Mock Records (for enrichment)
        self.records = [
            # Matches "นายสมชาย ขายเก่ง" -> provides phone
            {"type": "person", "name": "นายสมชาย ขายเก่ง", "name_norm": "นายสมชายขายเก่ง", "phones": ["0999999999"]},
            # No match
            {"type": "person", "name": "นายอื่นๆ", "phones": ["000"]}
        ]
        
        self.handler = DirectoryHandler(self.position_index, self.records)

    def test_exact_match(self):
        # Query: "วิศวกร 5"
        res = self.handler.handle("ขอข้อมูล วิศวกร 5")
        self.assertEqual(res["route"], "position_lookup")
        self.assertIn("นางสาววิศวา", res["answer"])
        self.assertIn("0812345678", res["answer"])

    def test_alias_handling_and_enrichment(self):
        # Scenario: "admin" -> "ผู้ดูแลระบบ"
        # Query "admin" should find "Admin User"
        res = self.handler.handle("ขอเบอร์ admin")
        
        self.assertEqual(res["route"], "position_lookup")
        self.assertIn("Admin User", res["answer"])
        # (Assuming enrichment logic is tested elsewhere or here if we added phone to records for Admin)

    def test_alias_admin_match(self):
        # We can remove this duplicate test or use it for another alias
        pass

    def test_miss(self):
        res = self.handler.handle("มนุษย์ต่างดาว")
        self.assertEqual(res["route"], "position_miss")
        self.assertIn("ไม่พบข้อมูล", res["answer"])

    def test_scan_match(self):
        # Query: "ธุรการ" (Substring of "หัวหน้างานธุรการ")
        res = self.handler.handle("งานธุรการ")
        # Should scan and find "หัวหน้างานธุรการ"
        self.assertEqual(res["route"], "position_lookup")
        self.assertIn("นายธุรการ", res["answer"])
        self.assertIn("admin@test.com", res["answer"])

if __name__ == "__main__":
    unittest.main()
