
import unittest
from src.rag.handlers.dispatch_mapper import DispatchMapper

class MockProcessedCache:
    def __init__(self, text_map):
        self._url_to_text = text_map

class TestDispatchMapperSparse(unittest.TestCase):
    def test_sparse_warning(self):
        # Simulated article: Ranong has code, Satun has only header
        article_text = """
การจ่ายงานเลขหมายวงจรเช่า
1. ระนอง
   XBN000201: Code (077-811111)
2. สตูล
   กองงานรวมสตูล
3. ยะลา
   YLA123: Valid
"""
        mock_cache = MockProcessedCache({
            "http://test.com/dispatch": article_text
        })
        
        # 1. Query Ranong -> Clean
        res = DispatchMapper.handle("การจ่ายงานเลขหมายวงจรเช่าระนอง", mock_cache)
        self.assertIn("XBN000201", res["answer"])
        self.assertNotIn("ไม่พบรหัส", res["answer"])
        
        # 2. Query Satun -> Header + Warning
        res = DispatchMapper.handle("การจ่ายงานเลขหมายวงจรเช่าสตูล", mock_cache)
        print(f"DEBUG Satun Answer: {res['answer']}")
        
        self.assertIn("กองงานรวมสตูล", res["answer"]) # Header preserved
        self.assertIn("ไม่พบรหัส/เลขหมายเพิ่มเติม", res["answer"]) # Warning added

if __name__ == "__main__":
    unittest.main()
