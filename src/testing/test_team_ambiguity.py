
import unittest
from src.rag.handlers.directory_handler import DirectoryHandler

class TestTeamAmbiguity(unittest.TestCase):
    def setUp(self):
        # Mock Data
        self.handler = DirectoryHandler(
            position_index={},
            records=[],
            team_index={
                "งาน HelpDesk": {"members": [{"name": "A"}]},
                "งาน Management SMC": {"members": [{"name": "B"}]},
                "งาน FTTx": {"members": [{"name": "C"}]}
            }
        )
        
    def test_classify_generic(self):
        # "smc" -> Generic
        is_amb, reason = self.handler._classify_ambiguity("smc", [])
        self.assertTrue(is_amb)
        self.assertEqual(reason, "generic")
        
        # "management" -> Generic
        is_amb, reason = self.handler._classify_ambiguity("management", [])
        self.assertTrue(is_amb)
        self.assertEqual(reason, "generic")
        
    def test_classify_short(self):
        # "ab" -> Short
        is_amb, reason = self.handler._classify_ambiguity("ab", [])
        self.assertTrue(is_amb)
        self.assertEqual(reason, "short")
        
    def test_classify_abbr(self):
        # "NOC" -> Abbr (Uppercase < 6 chars)
        is_amb, reason = self.handler._classify_ambiguity("NOC", [])
        self.assertTrue(is_amb)
        self.assertEqual(reason, "abbr")
        
    def test_classify_ok(self):
        # "HelpDesk" -> OK
        is_amb, reason = self.handler._classify_ambiguity("HelpDesk", ["งาน HelpDesk"])
        self.assertFalse(is_amb)
        
    def test_suggest_teams_ranking(self):
        # Query "SMC"
        # Prioritize containment
        matches = self.handler.suggest_teams("SMC")
        self.assertIn("งาน Management SMC", matches)
        
        # Fuzzy "HelpDask" -> "HelpDesk"
        matches = self.handler.suggest_teams("HelpDask")
        self.assertIn("งาน HelpDesk", matches)

if __name__ == "__main__":
    unittest.main()
