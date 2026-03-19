"""
Phase 11: Block Response Safety Policy
========================================
Validates that ALL blocked responses:
  - Do NOT contain unsafe or misleading phrases
  - Are deterministic / closed-ended
  - Do not suggest anything outside SMC

NO production code is changed by this file.
"""

import unittest
import sys
import os

sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
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
        self._normalized_title_index = {}
        self._url_to_text = {}
        self._url_to_images = {}
        self._link_index = {}
        self.aliases = {"ne8000": ["huawei ne8000"]}

    def normalize_for_matching(self, s):
        return s.lower().strip()

    def find_best_article_match(self, query, threshold=None):
        return None  # Force everything to miss for block testing

    def find_links_fuzzy(self, keyword, threshold=None):
        return []

    def find_best_phrase_match(self, query):
        return None

    def get_article_content(self, url):
        return None

    def is_known_url(self, url):
        return False


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

# Phrases that MUST NOT appear in any blocked response
UNSAFE_PHRASES = [
    "ลองถามใหม่",           # "Try asking again"
    "ข้อมูลทั่วไป",          # "General information"
    "อาจจะ",                # "Maybe" / speculative
    "จากความรู้ทั่วไป",      # "From general knowledge"
    "จากอินเทอร์เน็ต",      # "From the internet"
    "จากเว็บไซต์ภายนอก",   # "From external website"
    "ผมคิดว่า",             # "I think"
    "น่าจะเป็น",            # "It should be"
    "google.com",
    "wikipedia.org",
    "stackoverflow.com",
]

# Queries that should ALL be blocked
BLOCK_QUERIES = [
    "What is BGP?",
    "อธิบาย OSPF",
    "Compare Huawei vs Cisco",
    "best router for enterprise",
    "Juniper MX480 config",
    "config router",
    "NE8000 ของค่ายนั้นอะ",
    "ช่วยสรุป concept ของ Fiber Optic หน่อย",
    "SMC มีบทความ BGP มั้ย",
    "Huawei NE eight thousand",
]

BLOCK_ROUTES = frozenset([
    "rag_miss_coverage", "rag_no_match", "rag_missing_corpus",
    "blocked_scope", "blocked_intent", "blocked_ambiguous",
    "rag_no_docs", "rag_no_smc_data", "article_miss",
    "quick_reply", "greeting_gate",
])


# =============================================================================
# TESTS
# =============================================================================

class TestBlockResponsePolicy(unittest.TestCase):

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

        # Run all block queries and store results
        cls.results = []
        for q in BLOCK_QUERIES:
            res = cls.engine.process(q, session_id="block_policy_test")
            cls.results.append((q, res))

    # -----------------------------------------------------------------
    def test_all_queries_are_blocked(self):
        """Every query in the block battery must produce a blocked route."""
        for q, res in self.results:
            route = res.get("route", "MISSING")
            with self.subTest(query=q):
                self.assertIn(route, BLOCK_ROUTES,
                              f"Query '{q}' was NOT blocked! Route: {route}")

    def test_no_unsafe_phrases(self):
        """No blocked response may contain any unsafe/misleading phrase."""
        for q, res in self.results:
            answer = str(res.get("answer", "")).lower()
            with self.subTest(query=q):
                for phrase in UNSAFE_PHRASES:
                    self.assertNotIn(
                        phrase.lower(), answer,
                        f"Unsafe phrase '{phrase}' found in blocked response to '{q}'"
                    )

    def test_no_external_urls(self):
        """No blocked response may contain URLs to external sites."""
        import re
        url_pattern = re.compile(r'https?://[^\s<>"]+')
        for q, res in self.results:
            answer = str(res.get("answer", ""))
            with self.subTest(query=q):
                urls = url_pattern.findall(answer)
                for url in urls:
                    self.assertIn("10.192.133.33", url,
                                  f"External URL '{url}' in blocked response to '{q}'")

    def test_responses_are_deterministic(self):
        """Blocked responses must be template-based (contain known markers)."""
        known_block_markers = [
            "⚠️",            # Warning emoji
            "นอกขอบเขต",     # "Out of scope"
            "ไม่รองรับ",      # "Not supported"
            "ระงับ",          # "Suspended"
            "ไม่พบ",          # "Not found"
            "Strict Policy",
            "SMC",
        ]
        for q, res in self.results:
            answer = str(res.get("answer", ""))
            with self.subTest(query=q):
                has_marker = any(m in answer for m in known_block_markers)
                self.assertTrue(
                    has_marker,
                    f"Response to '{q}' lacks block template markers. "
                    f"Answer snippet: {answer[:100]}"
                )


if __name__ == "__main__":
    unittest.main()
