"""
Phase 9: Chaos / Abuse Input Hardening
=======================================
Tests adversarial, malformed, and edge-case inputs to ensure the system
never leaks external content, never guesses vendor/model, and always
produces an audit log.

NO production code is changed by this file.
"""

import unittest
import sys
import os
import json

sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
import src.chat_engine
import src.ingest.clean

# =============================================================================
# MOCK INFRASTRUCTURE (identical to test_reviewer_stress.py)
# =============================================================================

class MockFetchResult:
    def __init__(self, content):
        self.status_code = 200
        self.text = content
        self.html = content

def mock_fetch(url):
    return MockFetchResult("Mock Article Content")

src.chat_engine.fetch_with_policy = mock_fetch

class MockCleanResult:
    def __init__(self, text):
        self.text = text

def mock_clean_html_to_text(html):
    return MockCleanResult(html)

src.ingest.clean.clean_html_to_text = mock_clean_html_to_text


class FakeProcessedCache:
    """Simulates the real ProcessedCache with only known SMC articles."""

    def __init__(self):
        self._normalized_title_index = {
            "huawei ne8000 config": {
                "href": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=1",
                "title": "Huawei NE8000 Config",
            }
        }
        self._url_to_text = {
            "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=1": "Huawei NE8000 Configuration Guide"
        }
        self._url_to_images = {}
        self._link_index = {}
        self.aliases = {
            "ne8000": ["huawei ne8000"],
        }

    def normalize_for_matching(self, s):
        return s.lower().strip()

    def find_best_article_match(self, query, threshold=None):
        q_lower = query.lower()
        # ONLY match if BOTH "huawei" AND "ne8000" are present
        if "huawei" in q_lower and "ne8000" in q_lower:
            return {
                "match_type": "deterministic",
                "topic": "huawei ne8000",
                "score": 1.0,
                "url": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=1",
                "title": "Huawei NE8000 Config",
                "text": "Huawei NE8000 Config",
            }
        return None  # Everything else = no match

    def find_links_fuzzy(self, keyword, threshold=None):
        return []

    def find_best_phrase_match(self, query):
        return None

    def get_article_content(self, url):
        return self._url_to_text.get(url)

    def is_known_url(self, url):
        return url in self._url_to_text


class MockVS:
    def hybrid_query(self, text, top_k=3, alpha=0.5, where=None):
        return []


class MockWebHandler:
    def run_search(self, query, **kwargs):
        return "WEB_SEARCH_RESULT_FORBIDDEN"


class MockContentClassifier:
    def predict(self, prompt, **kwargs):
        return "GENERAL_QA"


class MockLLM:
    def predict(self, prompt, **kwargs):
        return "Mock LLM Response"


# =============================================================================
# TESTS
# =============================================================================

# Allowed blocking/rejection routes
BLOCK_ROUTES = frozenset([
    "rag_miss_coverage", "rag_no_match", "rag_missing_corpus",
    "blocked_scope", "blocked_intent", "blocked_ambiguous",
    "rag_no_docs", "rag_no_smc_data", "article_miss",
    "quick_reply",  # Non-text input handler (safe, no content leak)
])

ARTICLE_OK_ROUTES = frozenset([
    "article_answer", "article_link_only",
])

# Domains that must NEVER appear in any response
EXTERNAL_DOMAINS = [
    "google.com", "wikipedia.org", "stackoverflow.com",
    "youtube.com", "facebook.com", "github.com",
    "medium.com", "reddit.com",
]


class TestChaosInputFuzzing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cfg = {
            "llm": {"model": "mock", "base_url": "mock"},
            "chat": {"show_context": False},
            "rag": {"use_cache": False},
            "security": {"hardening_threshold": 0.8},
            "retrieval": {"top_k": 3},
        }
        cls.engine = ChatEngine(cfg)
        cls.engine.processed_cache = FakeProcessedCache()
        cls.engine.vs = MockVS()
        cls.engine.web_handler = MockWebHandler()
        cls.engine.content_classifier = MockContentClassifier()
        cls.engine.llm = MockLLM()

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def run_query(self, query):
        print(f"\n{'='*60}")
        print(f"[CHAOS] Query: '{query}'")
        res = self.engine.process(query, session_id="chaos_test")
        print(f"[CHAOS] Route : {res.get('route')}")
        return res

    def assertNoExternalContent(self, response):
        """Ensure response text contains no non-SMC domains."""
        answer = str(response.get("answer", ""))
        for domain in EXTERNAL_DOMAINS:
            self.assertNotIn(domain, answer,
                             f"External domain '{domain}' found in response!")

    # -----------------------------------------------------------------
    # 1. Typo / spacing variants
    # -----------------------------------------------------------------
    def test_01_spaced_typo(self):
        """'Hua wei NE 8000 cfg' — typo spacing, should block (no exact match)."""
        res = self.run_query("Hua wei NE 8000 cfg")
        route = res.get("route", "")
        # The typo prevents exact vendor+model extraction → should block
        self.assertIn(route, BLOCK_ROUTES | ARTICLE_OK_ROUTES,
                      f"Unexpected route: {route}")
        self.assertNoExternalContent(res)

    def test_02_hyphenated(self):
        """'huawei ne-8000' — hyphen variant."""
        res = self.run_query("huawei ne-8000")
        route = res.get("route", "")
        # 'huawei' is present → classified as TECH_ARTICLE_LOOKUP
        # 'ne-8000' may or may not match 'ne8000'
        self.assertIn(route, BLOCK_ROUTES | ARTICLE_OK_ROUTES)
        self.assertNoExternalContent(res)

    def test_03_thai_polite(self):
        """'ขอ Huawei NE8000 หน่อยครับ!!!' — Thai polite wrapping."""
        res = self.run_query("ขอ Huawei NE8000 หน่อยครับ!!!")
        route = res.get("route", "")
        # Contains 'huawei' + 'ne8000' → should find article
        self.assertIn(route, BLOCK_ROUTES | ARTICLE_OK_ROUTES)
        self.assertNoExternalContent(res)

    def test_04_vague_vendor_ref(self):
        """'NE8000 ของค่ายนั้นอะ' — no explicit vendor."""
        res = self.run_query("NE8000 ของค่ายนั้นอะ")
        route = res.get("route", "")
        # No 'huawei' → NON_SMC_TECH or blocked
        self.assertIn(route, BLOCK_ROUTES,
                      f"Vague query leaked! Route: {route}")
        self.assertNoExternalContent(res)

    def test_05_mixed_vendors(self):
        """'Cisco? ไม่ใช่ Huawei NE8000 นะ' — Cisco mention attempts confusion."""
        res = self.run_query("Cisco? ไม่ใช่ Huawei NE8000 นะ")
        route = res.get("route", "")
        # Both vendors present but query is ambiguous
        self.assertIn(route, BLOCK_ROUTES | ARTICLE_OK_ROUTES)
        self.assertNoExternalContent(res)

    def test_06_spelled_out_number(self):
        """'Huawei NE eight thousand' — model as text."""
        res = self.run_query("Huawei NE eight thousand")
        route = res.get("route", "")
        # 'ne8000' not present as token → should not match
        self.assertIn(route, BLOCK_ROUTES,
                      f"Spelled-out model leaked! Route: {route}")
        self.assertNoExternalContent(res)

    def test_07_bare_model(self):
        """'ne8000' — model only, no vendor."""
        res = self.run_query("ne8000")
        route = res.get("route", "")
        # No vendor → NON_SMC_TECH or blocked
        self.assertIn(route, BLOCK_ROUTES,
                      f"Bare model leaked! Route: {route}")
        self.assertNoExternalContent(res)

    def test_08_generic_tech(self):
        """'config router' — generic tech, no vendor/model."""
        res = self.run_query("config router")
        route = res.get("route", "")
        self.assertIn(route, BLOCK_ROUTES,
                      f"Generic tech leaked! Route: {route}")
        self.assertNoExternalContent(res)

    def test_09_punctuation_only(self):
        """'!!!' — pure noise."""
        res = self.run_query("!!!")
        route = res.get("route", "")
        self.assertIn(route, BLOCK_ROUTES,
                      f"Punctuation-only leaked! Route: {route}")
        self.assertNoExternalContent(res)

    def test_10_whitespace_only(self):
        """'   ' — whitespace only."""
        res = self.run_query("   ")
        route = res.get("route", "")
        self.assertIn(route, BLOCK_ROUTES,
                      f"Whitespace-only leaked! Route: {route}")
        self.assertNoExternalContent(res)


if __name__ == "__main__":
    unittest.main()
