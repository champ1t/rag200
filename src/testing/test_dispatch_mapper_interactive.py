
import unittest
from unittest.mock import Mock
from src.rag.handlers.dispatch_mapper import DispatchMapper

class TestDispatchMapperInteractive(unittest.TestCase):
    def setUp(self):
        # Mock Content based on assumed structure
        self.mock_text = """
        การจ่ายงานเลขหมายวงจรเช่า
        
        1. รายละเอียดพื้นที่
        
        กองงานระนอง
        ระนอง 100: 077001001
        
        2. ขั้นตอนการส่ง SMS
        ให้ส่งไปที่เบอร์ 1111
        - ใส่รหัสจังหวัด
        - ใส่เบอร์ติดต่อกลับ
        
        3. กรณีสาเหตุส่วนกลาง
        ให้แจ้ง NOC 1500
        """
        self.mock_cache = Mock()
        self.mock_cache._url_to_text = {"doc.json": self.mock_text}

    def test_query_province_default(self):
        # Case 1: Ask Province -> Get Province + Suggestion Footer
        res = DispatchMapper.handle("ระนอง", self.mock_cache)
        ans = res["answer"]
        
        # Verify Content
        self.assertIn("ระนอง", ans)
        self.assertIn("077001001", ans)
        
        # Verify Suggestions
        self.assertIn("ถ้าต้องการแนวทางส่ง SMS", ans)
        self.assertIn("พิมพ์ 'ข้อ 2'", ans)
        
        # Verify Item 2/3 Hidden
        self.assertNotIn("ส่งไปที่เบอร์ 1111", ans)
        self.assertNotIn("แจ้ง NOC 1500", ans)

    def test_query_sms_intent(self):
        # Case 2: Ask for SMS / Item 2
        res = DispatchMapper.handle("ขอวิธีส่ง SMS", self.mock_cache)
        ans = res["answer"]
        
        self.assertIn("ข้อ 2: แนวทางส่ง SMS", ans)
        self.assertIn("ส่งไปที่เบอร์ 1111", ans)
        # Should NOT show province data if not requested
        self.assertNotIn("ระนอง", ans)

    def test_query_central_intent(self):
        # Case 3: Ask for Central / Item 3
        res = DispatchMapper.handle("สาเหตุส่วนกลาง", self.mock_cache)
        ans = res["answer"]
        
        self.assertIn("ข้อ 3: กรณีสาเหตุอยู่ส่วนกลาง", ans)
        self.assertIn("แจ้ง NOC 1500", ans)
        
    def test_section_parsing_debug(self):
        # Just to check internal parsing map
        from src.utils.extractors import strip_footer_noise
        cleaned = strip_footer_noise(self.mock_text)
        # Access private method for testing logic
        data_map = DispatchMapper._parse_dispatch_article(cleaned)
        
        print("\nDEBUG MAP KEYS:", data_map.keys())
        self.assertIn("SECTION_2", data_map)
        self.assertIn("SECTION_3", data_map)
        self.assertIn("ระนอง", data_map)

if __name__ == "__main__":
    unittest.main()
