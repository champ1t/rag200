
import unittest
from src.rag.handlers.dispatch_mapper import DispatchMapper

class TestDispatchMapperNoise(unittest.TestCase):
    def test_noise_filtering(self):
        # Simulated article content with Noise
        article_text = """
การจ่ายงานเลขหมายวงจรเช่า
1. ระนอง
   XBN000201: สื่อสารข้อมูล 1 (077-811111)
2. สตูล
   (ไม่มีข้อมูล code)
   
คู่มือการใช้งาน:
- ต้องทำแบบนี้
- Joomla Template by NT
- แก้ไขล่าสุด 2024
3. ยะลา
   YLA1234: Test
"""
        # Parse
        data_map = DispatchMapper._parse_dispatch_article(article_text)
        
        # 1. Ranong should be fine
        self.assertIn("ระนอง", data_map)
        self.assertIn("XBN000201", data_map["ระนอง"])
        
        # 2. Satun: Should NOT contain "Joomla" or "คู่มือ"
        # Current logic might scoop "คู่มือ" into Satun buffer until it hits "ยะลา"
        if "สตูล" in data_map:
            satun_content = data_map["สตูล"]
            print(f"DEBUG Satun Content: {satun_content}")
            self.assertNotIn("Joomla", satun_content)
            self.assertNotIn("คู่มือ", satun_content)
            
        # 3. Stop Word "คู่มือ" should probably prevent "ยะลา" from being parsed? 
        # Or "ยะลา" is valid?
        # Requirement: "Stop when hit manual/footer".
        # If "ยะลา" is AFTER footer, maybe it's valid? 
        # Usually footer is at bottom. 
        # If Yala is after footer, it might be valid if it's a real header.
        # But commonly "Joomla" is the very end.
        
    def test_strict_line_validation(self):
        text = """
สงขลา
SNA001: Valid Map
This is just some random text description
That should be ignored
074-999999 Valid Phone
"""
        data_map = DispatchMapper._parse_dispatch_article(text)
        content = data_map.get("สงขลา", "")
        self.assertIn("SNA001", content)
        self.assertIn("074-999999", content)
        self.assertNotIn("random text", content)

if __name__ == "__main__":
    unittest.main()
