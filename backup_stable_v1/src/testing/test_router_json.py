import unittest
from unittest.mock import MagicMock, patch
from src.ai.router import IntentRouter

class TestRouterJSON(unittest.TestCase):
    def setUp(self):
        # Mock Config prevents real LLM calls
        self.mock_config = {"base_url": "mock", "model": "mock", "llm": {}}
        self.router = IntentRouter(self.mock_config)

    @patch("src.rag.ollama_client.ollama_generate")
    def test_clean_json(self, mock_llm):
        """Test standard clean JSON output."""
        mock_llm.return_value = '{"intent": "TEAM_LOOKUP", "confidence": 0.9, "reason": "Test"}'
        res = self.router._route_llm("test query")
        self.assertEqual(res["intent"], "TEAM_LOOKUP")
        self.assertEqual(res["confidence"], 0.9)

    @patch("src.rag.ollama_client.ollama_generate")
    def test_markdown_json(self, mock_llm):
        """Test Markdown code block wrapping."""
        mock_llm.return_value = '```json\n{\n "intent": "HOWTO_PROCEDURE",\n "confidence": 0.8\n}\n```'
        res = self.router._route_llm("test query")
        self.assertEqual(res["intent"], "HOWTO_PROCEDURE")

    @patch("src.rag.ollama_client.ollama_generate")
    def test_extra_text(self, mock_llm):
        """Test extra text around JSON."""
        mock_llm.return_value = 'Sure! Here is the JSON:\n{"intent": "CONTACT_LOOKUP", "confidence": 0.95}\nHope this helps.'
        res = self.router._route_llm("test query")
        self.assertEqual(res["intent"], "CONTACT_LOOKUP")

    @patch("src.rag.ollama_client.ollama_generate")
    def test_single_quotes(self, mock_llm):
        """Test single quotes fallback."""
        # Note: 'confidence' value might be unquoted if float, but keys might be single quoted.
        mock_llm.return_value = "{'intent': 'NEWS_SEARCH', 'confidence': 0.7}"
        res = self.router._route_llm("test query")
        self.assertEqual(res["intent"], "NEWS_SEARCH")

    @patch("src.rag.ollama_client.ollama_generate")
    def test_invalid_enum(self, mock_llm):
        """Test hallucinated intent Enum."""
        mock_llm.return_value = '{"intent": "HALLUCINATED_INTENT", "confidence": 1.0}'
        res = self.router._route_llm("test query")
        self.assertEqual(res["intent"], "GENERAL_QA")  # Should fallback
        
    @patch("src.rag.ollama_client.ollama_generate")
    def test_broken_json_raises(self, mock_llm):
        """Test badly broken JSON raises ValueError (which is caught in route())."""
        mock_llm.return_value = '{"intent": "BROKEN...'
        with self.assertRaises(ValueError):
            self.router._route_llm("test query")

if __name__ == "__main__":
    unittest.main()
