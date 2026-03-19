
import unittest
from src.rag.handlers.dispatch_mapper import DispatchMapper

class TestDispatchMapperStrict(unittest.TestCase):
    def test_strict_extraction(self):
        # Snippet from real issue
        article_text = """
การจ่ายงานเลขหมายวงจรเช่า
1. ระนอง
   XBN000201: สื่อสารข้อมูล 1 (077-811111)
2. สตูล
   กองงานรวม
   2. ให้ดำเนินการส่ง SMS แจ้งการจ่ายงานวงจรเช่าทุกครั้งเมื่อมีการจ่ายงานไปยังพื้นที่
   a. รูปแบบข้อความ SMS ประกอบด้วย :-
   เวลาที่ส่ง, เลขหมายวงจรเช่า, ชื่อลูกค้า, พื้นที่จังหวัด (xx.)
   ตัวอย่างดังนี้ "11.30:7724D0011"
   c. URL สำหรับส่ง SMS : http://203.113.6.76/SMS_APP
   3. กรณีดำเนินการวิเคราะห์วิเคราะห์เหตุเสียแล้ว สาเหตุเหตุเสียอยู่ในรับผิดชอบของส่วนงานส่วนกลาง
"""
        data_map = DispatchMapper._parse_dispatch_article(article_text)
        
        # 1. Ranong: Must pass
        self.assertIn("ระนอง", data_map)
        self.assertIn("XBN000201", data_map["ระนอง"])
        
        # 2. Satun: 
        # "กองงานรวม" might be valid unit keyword?
        # BUT "2. ให้ดำเนินการ..." MUST be filtered out.
        # "URL..." MUST be filtered out.
        
        if "สตูล" in data_map:
            content = data_map["สตูล"]
            print(f"DEBUG Satun Content: {content}")
            
            self.assertNotIn("ให้ดำเนินการ", content)
            self.assertNotIn("SMS", content)
            self.assertNotIn("URL", content)
            self.assertNotIn("ตัวอย่าง", content)
            
            # If "กองงานรวม" is considered valid unit, it might remain. That's acceptable.
            # But the long policy text must go.

if __name__ == "__main__":
    unittest.main()
