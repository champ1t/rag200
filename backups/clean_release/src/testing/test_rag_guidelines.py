"""
Phase 93: RAG Behavior Guidelines - Regression Tests

Tests for System Guidelines compliance:
1. Data boundary enforcement (no hallucination)
2. Ambiguity clarification (real candidates only)
3. Structured commands (show all)
4. Sensitive content protection
5. Index-only responses
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.rag.handlers.directory_handler import DirectoryHandler

class TestRAGGuidelines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("[SETUP] Initializing DirectoryHandler with mock data...")
        cls.handler = DirectoryHandler([], [])
        
        # Mock team_index with known teams
        cls.handler.team_index = {
            "HelpDesk": {"members": [{"name": "คนที่ 1"}]},
            "FTTx": {"members": [{"name": "คนที่ 2"}]},
            "Management SMC": {"members": [{"name": "คนที่ 3"}]}
        }

    def test_guideline1_data_boundary(self):
        """Rule 1: Return team_miss with structural reason when team not in index."""
        result = self.handler.handle_team_lookup("สมาชิกงาน NonExistentTeam123")
        
        self.assertEqual(result["route"], "team_miss")
        self.assertIn("ไม่พบ", result["answer"])
    
    def test_guideline2_ambiguity_real_candidates(self):
        """Rule 2: Ambiguous responses must have REAL candidates from index."""
        # This would need alias candidates that fuzzy match multiple teams
        # For now, verify that if we get suggestions, they're from real index
        result = self.handler.handle_team_lookup("สมาชิกงาน H")  # Short query
        
        # Should either hit, miss, or return ambiguous
        # If ambiguous, verify suggestions are real
        if result["route"] == "team_ambiguous":
            # Parse suggestions from answer (if present)
            # Verify they match keys in team_index
            pass  # Placeholder for detailed parsing
    
    def test_guideline3_show_all_structured(self):
        """Rule 3: 'Show all' must return ALL teams without fuzzy matching."""
        result = self.handler.handle_team_lookup("รายชื่อทีมทั้งหมด")
        
        self.assertEqual(result["route"], "team_list_all")
        self.assertIn("HelpDesk", result["answer"])
        self.assertIn("FTTx", result["answer"])
        self.assertIn("Management SMC", result["answer"])
        self.assertIn("3 ทีม", result["answer"])  # Count verification
    
    def test_guideline3_show_all_variations(self):
        """Rule 3: Various 'show all' keywords should work."""
        variations = [
            "แสดงทีมทั้งหมด",
            "มีทีมอะไรบ้าง",
            "show all teams",
            "list all"
        ]
        
        for query in variations:
            result = self.handler.handle_team_lookup(query)
            self.assertEqual(result["route"], "team_list_all", f"Failed for: {query}")
    
    def test_guideline5_index_only(self):
        """Rule 5: Results must come from index only (no hallucination)."""
        result = self.handler.handle_team_lookup("สมาชิกงาน HelpDesk")
        
        # If hit, verify team is in our mock index
        if result["route"] == "team_hit":
            self.assertIn("HelpDesk", result["answer"])
        
        # Should never return a team not in index
        self.assertNotIn("HallucinatedTeam", result["answer"])


class TestArticleSensitiveContent(unittest.TestCase):
    """Tests for Rule 4: Sensitive content protection"""
    
    @patch('src.rag.article_interpreter.ArticleInterpreter')
    def test_guideline4_sensitive_link_only(self, mock_interpreter):
        """Rule 4: Sensitive articles should return link-only."""
        # This test would verify ArticleInterpreter behavior
        # Checking that image-heavy + sensitive keywords = link only
        pass  # Placeholder - would need full ChatEngine setup
    
    def test_guideline4_no_password_extraction(self):
        """Rule 4: Never extract password tables."""
        # Verify that articles with "password" keywords don't extract content
        pass  # Placeholder - would need ArticleInterpreter test


if __name__ == "__main__":
    unittest.main()
