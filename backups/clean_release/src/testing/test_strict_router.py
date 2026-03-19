import unittest
from unittest.mock import patch, MagicMock
from src.ai.router import IntentRouter

class TestStrictRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter({"base_url": "mock", "model": "mock"})

    @patch("src.rag.ollama_client.ollama_generate")
    def test_llm_route_team(self, mock_gen):
        # Mock LLM response
        mock_gen.return_value = """```json
        {
            "intent": "TEAM_LOOKUP",
            "team": "งาน FTTx",
            "confidence": 0.9,
            "why": "User asked for personnel of FTTx"
        }
        ```"""
        
        res = self.router.route("บุคลากรงาน FTTx")
        self.assertEqual(res["intent"], "TEAM_LOOKUP")
        self.assertEqual(res["slots"]["team"], "งาน FTTx")
        self.assertEqual(res["reason"], "User asked for personnel of FTTx")

    @patch("src.rag.ollama_client.ollama_generate")
    def test_llm_route_contact_fallback(self, mock_gen):
        # Mock LLM Failure -> Fallback to Regex
        mock_gen.side_effect = Exception("Timeout")
        
        # Regex behavior for "ขอเบอร์คุณสมชาย" -> CONTACT_LOOKUP
        res = self.router.route("ขอเบอร์คุณสมชาย")
        self.assertEqual(res["intent"], "CONTACT_LOOKUP")
        self.assertEqual(res["reason"], "Contact Keyword Match")

if __name__ == "__main__":
    unittest.main()
