
import unittest
import sys
import os

# Adjust path to import from src
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.directory.build_records import validate_phone_digits, normalize_phone, parse_phones, norm

class TestPhoneParser(unittest.TestCase):

    def test_validate_phone_digits(self):
        # Mobile
        self.assertTrue(validate_phone_digits("0812345678"))
        self.assertTrue(validate_phone_digits("0912345678"))
        self.assertTrue(validate_phone_digits("0612345678"))
        
        # Landline 02
        self.assertTrue(validate_phone_digits("021234567"))   # 9 digits
        self.assertFalse(validate_phone_digits("0212345678")) # 10 digits for 02 is invalid (should be 9)
        
        # Provincial 03x, 04x, etc
        self.assertTrue(validate_phone_digits("038123456"))
        
        # Invalid
        self.assertFalse(validate_phone_digits("152"))        # too short
        self.assertFalse(validate_phone_digits("02123"))      # too short
        self.assertFalse(validate_phone_digits("0112345678")) # 01 is not standard mobile prefix usually
        self.assertFalse(validate_phone_digits("abc"))

    def test_normalize_phone(self):
        # Normal mobile
        num, ext = normalize_phone("081-234-5678")
        self.assertEqual(num, "081-234-5678")
        self.assertIsNone(ext)

        # Normal Landline
        num, ext = normalize_phone("02-123-4567")
        self.assertEqual(num, "02-123-4567")
        self.assertIsNone(ext)
        
        # No separator
        num, ext = normalize_phone("021234567")
        self.assertEqual(num, "02-123-4567")

        # With Extension
        num, ext = normalize_phone("02-123-4567 ต่อ 101")
        self.assertEqual(num, "02-123-4567")
        self.assertEqual(ext, "101")

        num, ext = normalize_phone("02-123-4567 #22")
        self.assertEqual(num, "02-123-4567")
        self.assertEqual(ext, "22")
        
        num, ext = normalize_phone("02-123-4567 ext. 333")
        self.assertEqual(num, "02-123-4567")
        self.assertEqual(ext, "333")

        # 'กด' extension
        num, ext = normalize_phone("02-123-4567 กด 9")
        self.assertEqual(num, "02-123-4567")
        self.assertEqual(ext, "9")
    def test_complex_extraction_id64(self):
        # Case 1: Ranges like 0-2575-4750-5 (Expect base number at least, ideally range expansion)
        # Note: Current logic might just drop the suffix or capture as separate if not careful.
        # Ideally: "025754750" is captured. 
        res1 = parse_phones("IP Network 0-2575-4750-5")
        # For now, let's just assert we get the main number. 
        # If the user wants "Every number", we might need validation if '5' becomes a number (it won't pass validate).
        self.assertIn("02-575-4755", res1) # If we support range expansion, otherwise checking for 4750
        
        # Case 2: Comma separated without space
        res2 = parse_phones("02-575-9846,02-575-9848")
        self.assertIn("02-575-9846", res2)
        self.assertIn("02-575-9848", res2)

        # Case 3: Mixed dashes and spaces
        res3 = parse_phones("025757222, 085-8135083")
        self.assertIn("02-575-7222", res3)
        self.assertIn("085-813-5083", res3)

        # Case 4: Suffix range 0-2575-4602-3
        res4 = parse_phones("0-2575-4602-3")
        self.assertIn("02-575-4602", res4)
        # self.assertIn("02-575-4603", res4) # Future goal

        # Case 5: 8-digit legacy
        res5 = parse_phones("0-2505-2157")
        self.assertIn("02-505-2157", res5)

        # Case 6: "กด" with spaces
        res6 = parse_phones("0-2104-1919 กด 2") 
        self.assertIn("02-104-1919 ต่อ 2", res6)

    def test_parse_phones_multi(self):
        text = "ติดต่อ 081-234-5678 หรือ 02-999-9999 ต่อ 11"
        results = parse_phones(text)
        self.assertIn("081-234-5678", results)
        self.assertIn("02-999-9999 ต่อ 11", results)
        self.assertEqual(len(results), 2)

    def test_parse_phones_dirty(self):
        text = "Tel:0812345678Fax:021234567"
        results = parse_phones(text)
        self.assertIn("081-234-5678", results)
        self.assertIn("02-123-4567", results)

if __name__ == '__main__':
    unittest.main()
