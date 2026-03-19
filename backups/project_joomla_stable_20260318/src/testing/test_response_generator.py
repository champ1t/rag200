import unittest
from unittest.mock import patch
from src.ai.response_generator import ResponseGenerator

class TestResponseGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = ResponseGenerator({"base_url": "mock", "model": "mock"})

    @patch("src.ai.response_generator.ollama_generate")
    def test_generate_success(self, mock_llm):
        mock_llm.return_value = "ข้อมูลบุคลากรงาน FTTx:\n- นาย A (หัวหน้า)\n- นาย B"
        
        res = self.gen.generate(
            query="บุคลากร FTTx",
            intent="TEAM_LOOKUP",
            result={"members": ["A", "B"]},
            available_teams=["งาน FTTx"]
        )
        self.assertIn("นาย A", res)

    @patch("src.ai.response_generator.ollama_generate")
    def test_generate_team_miss(self, mock_llm):
        mock_llm.return_value = "ไม่พบงาน 'Unknown'. งานที่ใกล้เคียงคือ:\n1. งาน FTTx\n2. งาน HelpDesk"
        
        res = self.gen.generate(
            query="งาน Unknown",
            intent="TEAM_LOOKUP",
            result=None,
            available_teams=["งาน FTTx", "งาน HelpDesk"]
        )
        self.assertIn("ไม่พบ", res)
        self.assertIn("FTTx", res)

if __name__ == "__main__":
    unittest.main()
