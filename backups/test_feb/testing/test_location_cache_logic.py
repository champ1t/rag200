
import unittest
from unittest.mock import MagicMock
from src.chat_engine import ChatEngine
from src.utils.section_filter import extract_location_intent, slice_markdown_section
from src.cache.semantic import SemanticCache

class TestLocationCacheLogic(unittest.TestCase):
    def test_fingerprint_generation(self):
        # Case 1: Generic query
        q1 = "internet slow"
        locs1 = extract_location_intent(q1)
        fp1 = "|".join(sorted(locs1)) if locs1 else "none"
        self.assertEqual(fp1, "none")
        
        # Case 2: Specific query
        q2 = "internet slow songkhla"
        locs2 = extract_location_intent(q2)
        fp2 = "|".join(sorted(locs2))
        self.assertEqual(fp2, "สงขลา")
        
        # Case 3: Multiple
        q3 = "surat and songkhla"
        locs3 = extract_location_intent(q3)
        fp3 = "|".join(sorted(locs3))
        # Sorted order "สงขลา|สุราษฎร์ธานี" (Thai sort?) or alphabetical?
        # Python sort is unicode based.
        self.assertTrue("สงขลา" in fp3 and "สุราษ" in fp3)

    def test_slice_fallback(self):
        content = "## 1. Songkhla\nData S\n## 2. Phuket\nData P"
        
        # Case A: Found
        slice1 = slice_markdown_section(content, ["สงขลา"])
        self.assertIn("Data S", slice1)
        self.assertNotIn("Data P", slice1)
        
        # Case B: Not Found (Trang)
        slice2 = slice_markdown_section(content, ["ตรัง"])
        self.assertIn("ไม่พบข้อมูลเฉพาะสำหรับจังหวัด **ตรัง**", slice2)
        self.assertIn("สงขลา", slice2) # Should list available
        self.assertIn("ภูเก็ต", slice2)

if __name__ == "__main__":
    unittest.main()
