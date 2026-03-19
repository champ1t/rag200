
import unittest
from unittest.mock import Mock
from src.rag.handlers.dispatch_mapper import DispatchMapper

class TestDispatchMapperMix(unittest.TestCase):
    def setUp(self):
        # Mock Cache with mixed content
        self.mixed_text = """
        การจ่ายงานเลขหมายวงจรเช่า
        
        กองงานรวมสตูล
        สตูล 300: 09891Z0300
        
        กองงานระนอง
        ระนอง 100: 077001001
        
        กองงานภูเก็ต
        ภูเก็ต 200: 076002002
        
        Footer:
        Joomla Template by ...
        Edocument Download
        Login Form
        """
        self.mock_cache = Mock()
        self.mock_cache._url_to_text = {"doc1.json": self.mixed_text}

    def test_query_ranong_isolates_output(self):
        # User asks for "Ranong"
        # Should get ONLY Ranong data.
        # Should NOT get Satun or Phuket.
        
        res = DispatchMapper.handle("ขอข้อมูระนอง", self.mock_cache)
        ans = res["answer"]
        
        print(f"DEBUG Output:\n{ans}")
        
        self.assertIn("ระนอง", ans)
        self.assertIn("077001001", ans)
        
        # Verify ISOLATION
        self.assertNotIn("สตูล", ans)
        self.assertNotIn("09891Z0300", ans)
        self.assertNotIn("ภูเก็ต", ans)
        
        # Verify NOISE STRIP
        self.assertNotIn("Joomla", ans)
        self.assertNotIn("Edocument", ans)
        self.assertNotIn("Login", ans)

    def test_query_multiple_provinces(self):
        # User asks "Ranong Phuket"
        res = DispatchMapper.handle("ระนอง ภูเก็ต", self.mock_cache)
        ans = res["answer"]
        
        self.assertIn("ระนอง", ans)
        self.assertIn("ภูเก็ต", ans)
        self.assertNotIn("สตูล", ans)

if __name__ == "__main__":
    unittest.main()
