
import unittest
from src.directory.extract_positions import is_valid_person_line

class TestTeamExtraction(unittest.TestCase):
    def test_strict_person_filter(self):
        # Valid Person Lines
        self.assertTrue(is_valid_person_line("นาย สมใจ รักดี"))
        self.assertTrue(is_valid_person_line("นางสาว ใจงาม"))
        self.assertTrue(is_valid_person_line("somjai@nt.com"))
        self.assertTrue(is_valid_person_line("074-123-4567"))
        self.assertTrue(is_valid_person_line("Agent 0-7427-1111"))
        
        # Invalid Garbage Lines
        self.assertFalse(is_valid_person_line("ลิงค์ภายใต้ ภก."))
        self.assertFalse(is_valid_person_line("ศูนย์บริการลูกค้า"))
        self.assertFalse(is_valid_person_line("ปรับปรุงระบบ"))
        self.assertFalse(is_valid_person_line("Visitors Counter"))
        self.assertFalse(is_valid_person_line("Main Menu"))

if __name__ == "__main__":
    unittest.main()
