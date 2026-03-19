
import unittest
from unittest.mock import MagicMock
from src.rag.handlers.dispatch_mapper import DispatchMapper

class MockProcessedCache:
    def __init__(self, text_map):
        self._url_to_text = text_map

class TestDispatchMapper(unittest.TestCase):
    def setUp(self):
        self.article_text = """
การจ่ายงานเลขหมายวงจรเช่า
(SCOMS)
1. ติดต่อ สงขลา
   เบอร์: 074-123456
   ผู้รับผิดชอบ: คุณ A
2. ติดต่อ สุราษฎร์ธานี
   เบอร์: 077-999999
   รายละเอียด: งานติดตั้ง
3. ภูเก็ต
   (ไม่มีข้อมูล)
"""
        self.mock_cache = MockProcessedCache({
            "http://test.com/dispatch": self.article_text
        })
        
    def test_is_match(self):
        self.assertTrue(DispatchMapper.is_match("ขอระเบียบการจ่ายงานเลขหมายวงจรเช่า"))
        self.assertTrue(DispatchMapper.is_match("SCOMS จ่ายงานยังไง"))
        self.assertFalse(DispatchMapper.is_match("ขอเบอร์โทรศัพท์")) # Missing keywords
        
    def test_parse_dispatch_article(self):
        data_map = DispatchMapper._parse_dispatch_article(self.article_text)
        self.assertIn("สงขลา", data_map)
        self.assertIn("สุราษฎร์ธานี", data_map)
        self.assertIn("ภูเก็ต", data_map)
        
        self.assertIn("074-123456", data_map["สงขลา"])
        self.assertIn("077-999999", data_map["สุราษฎร์ธานี"])
        
    def test_handle_specific_province(self):
        # Query for Songkhla
        res = DispatchMapper.handle("การจ่ายงานเลขหมายวงจรเช่าสงขลา", self.mock_cache)
        self.assertEqual(res["route"], "dispatch_mapper_hit")
        self.assertIn("**สงขลา**", res["answer"])
        self.assertNotIn("**สุราษฎร์ธานี**", res["answer"]) # Should be sliced
        
    def test_handle_missing_province(self):
        # Query for Trang (Not in doc)
        res = DispatchMapper.handle("การจ่ายงานเลขหมายวงจรเช่า ตรัง", self.mock_cache)
        self.assertEqual(res["route"], "dispatch_mapper_hit")
        self.assertIn("ไม่พบข้อมูลสำหรับ: ตรัง", res["answer"])
        self.assertIn("พื้นที่ที่มีข้อมูล", res["answer"])
        self.assertIn("สงขลา", res["answer"])

if __name__ == "__main__":
    unittest.main()
