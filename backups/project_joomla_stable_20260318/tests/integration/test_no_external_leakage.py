"""
Phase 10: No-External-Leakage Proof
====================================
For EVERY response from a battery of queries, assert:
  - route ∈ allowed set (no unknown routes)
  - response text contains NO non-SMC domains
  - audit log is written (metrics counter incremented)

NO production code is changed by this file.
"""

import unittest
import sys
import os
import json

sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.utils.metrics import MetricsTracker
import src.chat_engine
import src.ingest.clean

# =============================================================================
# MOCK INFRASTRUCTURE
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
        self.aliases = {"ne8000": ["huawei ne8000"]}

    def normalize_for_matching(self, s):
        return s.lower().strip()

    def find_best_article_match(self, query, threshold=None):
        q_lower = query.lower()
        if "huawei" in q_lower and "ne8000" in q_lower:
            return {
                "match_type": "deterministic", "topic": "huawei ne8000",
                "score": 1.0,
                "url": "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=1",
                "title": "Huawei NE8000 Config", "text": "Huawei NE8000 Config",
            }
        return None

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
# CONSTANTS
# =============================================================================

ALLOWED_ROUTES = frozenset([
    # Block / Rejection
    "rag_miss_coverage", "rag_no_match", "rag_missing_corpus",
    "blocked_scope", "blocked_intent", "blocked_ambiguous",
    "rag_no_docs", "rag_no_smc_data", "article_miss",
    "quick_reply",
    "greeting_gate",  # Safe greeting handler
    # Success (SMC only)
    "article_answer", "article_link_only",
])

EXTERNAL_DOMAINS = [
    "google.com", "wikipedia.org", "stackoverflow.com",
    "youtube.com", "facebook.com", "github.com",
    "medium.com", "reddit.com", "cisco.com", "huawei.com",
    "juniper.net", "networkworld.com",
]

QUERY_BATTERY = [
    # Valid SMC queries
    "Huawei NE8000 config",
    # Invalid / should-be-blocked queries
    "Cisco ASR920 setup guide",
    "What is BGP?",
    "อธิบาย OSPF",
    "Compare Huawei vs Cisco",
    "best router for enterprise",
    "Juniper MX480 config",
    "config router",
    "สวัสดี",
    "!!!",
    "   ",
    "NE8000 ของค่ายนั้นอะ",
    "Huawei feature overview",
    "ข้อดีข้อเสีย Huawei",
    "SMC มีบทความ BGP มั้ย",
]


# =============================================================================
# TESTS
# =============================================================================

class TestNoExternalLeakage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import shutil
        cls.log_dir = "logs_leakage_test"
        if os.path.exists(cls.log_dir):
            shutil.rmtree(cls.log_dir)
        os.makedirs(cls.log_dir)

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
        cls.engine.metrics = MetricsTracker(log_dir=cls.log_dir)

        # Run all queries and store results
        cls.results = []
        for q in QUERY_BATTERY:
            res = cls.engine.process(q, session_id="leakage_test")
            cls.results.append((q, res))

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists(cls.log_dir):
            shutil.rmtree(cls.log_dir)

    # -----------------------------------------------------------------
    def test_all_routes_are_allowed(self):
        """Every response must have a known, allowed route."""
        for q, res in self.results:
            route = res.get("route", "MISSING_ROUTE")
            with self.subTest(query=q):
                self.assertIn(route, ALLOWED_ROUTES,
                              f"Unknown route '{route}' for query '{q}'")

    def test_no_external_domains_in_responses(self):
        """No response text may contain any external domain."""
        for q, res in self.results:
            answer = str(res.get("answer", ""))
            with self.subTest(query=q):
                for domain in EXTERNAL_DOMAINS:
                    self.assertNotIn(
                        domain, answer.lower(),
                        f"External domain '{domain}' leaked in response to '{q}'"
                    )

    def test_no_non_smc_urls_in_responses(self):
        """No response may contain URLs that are not SMC (10.192.133.33)."""
        import re
        url_pattern = re.compile(r'https?://[^\s<>"]+')
        for q, res in self.results:
            answer = str(res.get("answer", ""))
            with self.subTest(query=q):
                urls = url_pattern.findall(answer)
                for url in urls:
                    self.assertIn("10.192.133.33", url,
                                  f"Non-SMC URL '{url}' in response to '{q}'")

    def test_audit_log_written_for_all(self):
        """Metrics must record every query."""
        stats_path = os.path.join(self.log_dir, "dashboard_stats.json")
        self.assertTrue(os.path.exists(stats_path), "Stats file not found")

        with open(stats_path, "r") as f:
            stats = json.load(f)

        expected_total = len(QUERY_BATTERY)
        actual_total = stats.get("total_queries", 0)
        self.assertEqual(actual_total, expected_total,
                         f"Expected {expected_total} logged queries, got {actual_total}")

    def test_valid_query_gets_article(self):
        """The known valid query must succeed via article_answer."""
        for q, res in self.results:
            if q == "Huawei NE8000 config":
                self.assertEqual(res.get("route"), "article_answer",
                                 f"Valid query '{q}' did not succeed!")
                return
        self.fail("Valid query 'Huawei NE8000 config' not found in battery")


if __name__ == "__main__":
    unittest.main()
