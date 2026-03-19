
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.directory.lookup import lookup_phones, lookup_by_phone, load_records

# Mock Records
MOCK_RECORDS = [
    {
        "name": "ศูนย์ RNOC หาดใหญ่",
        "name_norm": "ศูนย์ rnoc หาดใหญ่",
        "phones": ["074-856-174", "081-417-0144"],
        "type": "team",
        "tags": ["NOC"]
    },
    {
        "name": "คุณ เฉลิมรัตน์ อัศวทรงพล",
        "name_norm": "คุณ เฉลิมรัตน์ อัศวทรงพล",
        "phones": ["02-575-7222", "085-813-5083"],
        "type": "person",
        "tags": ["ADSL", "ศูนย์ RNOC หาดใหญ่"] # Tag match for team
    },
    {
        "name": "Radius NT1",
        "name_norm": "radius nt1",
        "phones": ["02-104-1919 กด 2"],
        "type": "team"
    }
]

class TestContactLookup(unittest.TestCase):

    def test_lookup_person_name(self):
        phones, rec = lookup_phones("เบอร์คุณ เฉลิมรัตน์", MOCK_RECORDS)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "คุณ เฉลิมรัตน์ อัศวทรงพล")
        self.assertIn("02-575-7222", phones)

    def test_lookup_team_name(self):
        phones, rec = lookup_phones("เบอร์ RNOC หาดใหญ่", MOCK_RECORDS)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "ศูนย์ RNOC หาดใหญ่")
        self.assertIn("074-856-174", phones)

    def test_reverse_lookup_phone(self):
        # Exact digits
        hits = lookup_by_phone("02-575-7222", MOCK_RECORDS)
        self.assertTrue(any(r["name"] == "คุณ เฉลิมรัตน์ อัศวทรงพล" for r in hits))

        # Partial format (no dashes)
        hits = lookup_by_phone("0814170144", MOCK_RECORDS)
        self.assertTrue(any(r["name"] == "ศูนย์ RNOC หาดใหญ่" for r in hits))

    def test_lookup_extension(self):
        phones, rec = lookup_phones("Radius NT1", MOCK_RECORDS)
        self.assertIsNotNone(rec)
        self.assertIn("02-104-1919 กด 2", phones)

    def test_not_found(self):
        phones, rec = lookup_phones("Unknown Entity", MOCK_RECORDS)
        self.assertIsNone(rec)
        self.assertEqual(phones, [])

        hits = lookup_by_phone("9999999999", MOCK_RECORDS)
        self.assertEqual(hits, [])

if __name__ == '__main__':
    unittest.main()
