
import unittest
from unittest.mock import MagicMock, patch
from src.ingest.fetch import fetch_url
from src.main import load_config

class TestCrawlerLogic(unittest.TestCase):
    def test_auth_detection_url_redirect(self):
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
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.error, "auth_required_url_redirect")

    def test_auth_detection_password_field(self):
        # Mock requests.get to return a response with password field
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.url = "http://example.com/page"
            mock_resp.text = "<html><form><input type='password'></form></html>"
            mock_resp.headers = {"Content-Type": "text/html"}
            mock_resp.status_code = 200
            mock_resp.apparent_encoding = "utf-8"
            mock_get.return_value = mock_resp

            res = fetch_url("http://example.com/page")
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.error, "auth_required_password_field")

    def test_config_deny_extensions(self):
        cfg = load_config("configs/config.yaml")
        deny = cfg["web"]["deny_extensions"]
        self.assertIn(".pdf", deny)
        self.assertIn(".zip", deny)
        self.assertIn(".exe", deny)
        self.assertTrue(len(deny) > 10)

if __name__ == "__main__":
    unittest.main()
