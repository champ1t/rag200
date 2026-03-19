import unittest
from unittest.mock import patch
from src.ai.team_resolver import TeamResolver

class TestTeamResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = TeamResolver({"base_url": "mock", "model": "mock"})
        self.candidates = ["งาน FTTx", "งาน HelpDesk", "งาน Management SMC"]

    @patch("src.ai.team_resolver.ollama_generate")
    def test_resolve_match(self, mock_gen):
        mock_gen.return_value = """{
            "status": "match",
            "canonical_team": "งาน FTTx",
            "candidates": ["งาน FTTx"],
            "why": "Exact match"
        }"""
        
        res = self.resolver.resolve("บุคลากรงาน FTTx", self.candidates)
        self.assertEqual(res["status"], "match")
        self.assertEqual(res["canonical_team"], "งาน FTTx")

    @patch("src.ai.team_resolver.ollama_generate")
    def test_resolve_ambiguous(self, mock_gen):
        mock_gen.return_value = """{
            "status": "ambiguous",
            "canonical_team": null,
            "candidates": ["งาน FTTx", "งาน HelpDesk"],
            "why": "Unclear input"
        }"""
        
        res = self.resolver.resolve("งาน", self.candidates)
        self.assertEqual(res["status"], "ambiguous")
        self.assertIsNone(res["canonical_team"])

if __name__ == "__main__":
    unittest.main()
