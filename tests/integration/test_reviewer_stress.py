
import unittest
import sys
import os
import time

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
import src.chat_engine
import src.ingest.clean

# =============================================================================
# MOCK INFRASTRUCTURE (Reused for consistency)
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
        self.aliases = {
            "ne8000": ["huawei ne8000"],
            "asr920": ["cisco asr920"]
        }
        self._url_to_text = {"http://mock/1": "Huawei NE8000 Config Content"}
        self._url_to_images = {}
        self._link_index = {}

    def normalize_for_matching(self, s):
        return s.lower().strip()

    def find_best_article_match(self, query, threshold=None):
        q_lower = query.lower()
        # Simulate SMC Content only for exact knowns
        if "huawei" in q_lower and "ne8000" in q_lower and "config" in q_lower:
             return {"match_type": "deterministic", "topic": "huawei ne8000", "score": 1.0, "url": "http://10.192.133.33/smc/article/1", "title": "Huawei NE8000 Config", "text": "Huawei NE8000 Config"}
        if "asr920" in q_lower:
             return {"match_type": "missing_corpus", "topic": "cisco asr920", "score": 1.0}
        return None 

    def find_links_fuzzy(self, keyword, threshold=None):
        return []

    def find_best_phrase_match(self, query):
        return None

    def get_article_content(self, url):
        return None

class MockVS:
    def hybrid_query(self, text, top_k=3, alpha=0.5, where=None):
        return [] # Empty for stress testing (force fallback checks)

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

class TestReviewerStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = {
            "llm": {"model": "mock", "base_url": "mock"},
            "chat": {"show_context": False},
            "rag": {"use_cache": False},
            "security": {"hardening_threshold": 0.8},
            "retrieval": {"top_k": 3}
        }
        cls.engine = ChatEngine(cfg)
        cls.engine.processed_cache = FakeProcessedCache()
        cls.engine.vs = MockVS()
        cls.engine.web_handler = MockWebHandler()
        cls.engine.content_classifier = MockContentClassifier()
        cls.engine.llm = MockLLM()
        cls.engine.load_records = lambda x: []

    def run_query(self, query):
        print(f"\n[Test] Query: '{query}'")
        return self.engine.process(query, session_id="test_stress")

    def assertBlocked(self, query, response):
        route = response.get("route", "unknown")
        # Allowed blocking/rejection routes
        allowed = ["rag_miss_coverage", "rag_no_match", "rag_missing_corpus", 
                   "blocked_scope", "blocked_intent", "rag_no_docs", "rag_no_smc_data"]
        
        if route not in allowed:
            self.fail(f"Query '{query}' leaked! Route: {route}. Expected one of: {allowed}")
        else:
            print(f"✅ Blocked/Rejected correctly via {route}")

    # 1. Comparison Queries (Explicitly Out of Scope)
    def test_comparisons(self):
        queries = [
            "เทียบ Cisco กับ Huawei จากเว็บ SMC", # Compare Cisco vs Huawei
            "Huawei NE8000 difference ASR920",
            "Cisco vs Huawei pros cons",
            "ข้อดีข้อเสีย Huawei NE8000" # Pros/Cons (Opinion)
        ]
        for q in queries:
            with self.subTest(q=q):
                res = self.run_query(q)
                self.assertBlocked(q, res)

    # 2. General Knowledge / Mixed Language (Non-SMC)
    def test_general_knowledge_mixed(self):
        queries = [
            "SMC มีบทความอธิบาย BGP ทั่วไปมั้ย", # SMC have article explain BGP general?
            "อธิบาย OSPF แบบไม่ต้องอ้างอิงบทความ", # Explain OSPF without referencing article
            "What is MPLS standard definition?",
            "ช่วยสรุป concept ของ Fiber Optic หน่อย" # Summarize concept...
        ]
        for q in queries:
            with self.subTest(q=q):
                res = self.run_query(q)
                self.assertBlocked(q, res)

    # 3. Partial / Misleading Matches
    def test_partial_misleading(self):
        queries = [
            "Huawei feature", # Too vague
            "Cisco setup", # Too vague
            "Config router", # No vendor
            "SMC manuals", # Meta query
        ]
        for q in queries:
            with self.subTest(q=q):
                res = self.run_query(q)
                self.assertBlocked(q, res)
    
    # 4. Control: Valid Query (Should Pass)
    def test_valid_control(self):
        q = "Huawei NE8000 config"
        res = self.run_query(q)
        self.assertEqual(res.get("route"), "article_answer", f"Control query '{q}' failed!")
        print(f"✅ Control passed: {q} -> article_answer")

if __name__ == "__main__":
    unittest.main()
