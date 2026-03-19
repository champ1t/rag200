
import unittest
from unittest.mock import MagicMock, patch
from src.ingest.fetch import fetch_url
from src.main import load_config

class TestCrawlerAuthLogic(unittest.TestCase):
    def test_auth_replacement_logic(self):
        # Mock requests.get to return a response with login URL
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.url = "http://example.com/login"
            mock_resp.text = "<html>Login here</html>"
            mock_resp.headers = {"Content-Type": "text/html"}
            mock_resp.status_code = 200
            mock_resp.apparent_encoding = "utf-8"
            mock_get.return_value = mock_resp

            res = fetch_url("http://example.com/some-page")
            
            # Should now be 200, not 403
            self.assertEqual(res.status_code, 200)
            self.assertIn("Authentication Required", res.html)
            self.assertIn("click here to login", res.html)
            self.assertEqual(res.error, "")

if __name__ == "__main__":
    unittest.main()
