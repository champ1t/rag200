
import unittest
from src.utils.section_filter import extract_location_intent, slice_markdown_section

class TestLocationLogic(unittest.TestCase):
    def test_extract_location(self):
        # Normal
        self.assertEqual(extract_location_intent("ขอข้อมูล สงขลา"), ["สงขลา"])
        # Abbr
        self.assertEqual(extract_location_intent("ขอข้อมูล สุราษ"), ["สุราษฎร์ธานี"])
        self.assertEqual(extract_location_intent("กทม มีอะไรบ้าง"), ["กรุงเทพ"])
        # Multi
        locs = extract_location_intent("สงขลา และ ภูเก็ต")
        self.assertIn("สงขลา", locs)
        self.assertIn("ภูเก็ต", locs)
        # None
        self.assertEqual(extract_location_intent("ไม่มีจังหวัด"), [])
        
    def test_slice_section_header(self):
        content = """
# Header Global
General info.

## 1. สงขลา
Detail Songkhla 1
Detail Songkhla 2

## 2. ภูเก็ต
Detail Phuket 1

### 3. สุราษฎร์ธานี (Surat)
Detail Surat
"""
        # Test Songkhla slicing
        sliced = slice_markdown_section(content, ["สงขลา"])
        print(f"Sliced Songkhla:\n{sliced}")
        self.assertIn("Section 1. สงขลา", sliced.replace("## ", "Section ")) # Loose check
        self.assertIn("Detail Songkhla", sliced)
        self.assertNotIn("Phuket", sliced)
        self.assertNotIn("Surat", sliced)
        
        # Test Surat slicing
        sliced_surat = slice_markdown_section(content, ["สุราษฎร์ธานี"])
        self.assertIn("Detail Surat", sliced_surat)
        self.assertNotIn("Songkhla", sliced_surat)
        
    def test_slice_list_item(self):
        content = """
Title: Service Areas

1. สงขลา: 074-xxx
2. ภูเก็ต: 076-xxx (Active)
3. ยะลา: 073-xxx
"""
        sliced = slice_markdown_section(content, ["ภูเก็ต"])
        self.assertIn("ภูเก็ต: 076-xxx", sliced)
        self.assertNotIn("สงขลา", sliced)
        self.assertNotIn("ยะลา", sliced)

if __name__ == "__main__":
    unittest.main()
