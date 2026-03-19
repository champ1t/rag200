import sys
import os
import json
import time
from typing import Dict, Any, Optional

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

# =============================================================================
# MOCK INFRASTRUCTURE
# =============================================================================

# Mock fetch_with_policy to prevent network calls
import src.chat_engine

class MockFetchResult:
    def __init__(self, content):
        self.status_code = 200
        self.text = content
        self.page_content = content
        self.html = content

def mock_fetch(url):
    print(f"DEBUG: Mock Fetch called for {url}")
    return MockFetchResult("Mock Article Content for " + url)

src.chat_engine.fetch_with_policy = mock_fetch

class FakeProcessedCache:
    def __init__(self):
        self._normalized_title_index = {}
        self._url_to_text = {}
        self._url_to_images = {}
        self._link_index = {}
        self.aliases = {
            "ne8000": ["huawei ne8000"],
            "asr920": ["cisco asr920"],
            "c300": ["zte c300"]
        }
        # Pre-load some fake articles for deterministic matching
        self.articles = {
            "Huawei NE8000 Config": {
                "title": "Huawei NE8000 Configuration Guide",
                "text": "Full config guide for NE8000...",
                "url": "http://10.192.133.33/ne8000/config",
                "topic": "huawei ne8000",
                "match_type": "deterministic",
                "score": 1.0
            },
            "Cisco ASR920 Command": {
                "title": "Cisco ASR920 Command Reference",
                "text": "Commands for ASR920...",
                "url": "http://10.192.133.33/asr920/cmd",
                "topic": "cisco asr920",
                "match_type": "deterministic",
                "score": 1.0
            },
            "Huawei NE8000 Overview": {
                "title": "Huawei NE8000 Overview",
                "text": "Introduction to NE8000...",
                "url": "http://10.192.133.33/ne8000/overview",
                "topic": "huawei ne8000",
                "match_type": "deterministic",
                "score": 1.0
            },
            "Troubleshoot 577K": {
                "title": "Troubleshooting Huawei 577K SNR",
                "text": "How to fix low SNR...",
                "url": "http://10.192.133.33/577k/ts",
                "topic": "huawei 577k",
                "match_type": "deterministic",
                "score": 1.0
            }
        }

    def normalize_for_matching(self, text: str) -> str:
        return text.lower().strip()

    def find_best_article_match(self, query: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        q_lower = query.lower()
        print(f"DEBUG: find_best_article_match q='{query}'")
        
        # Simulate Ambiguity Check (Test Case C4)
        if "ambiguous" in q_lower:
            print("DEBUG: Returning Ambiguous")
            return {
                "match_type": "ambiguous",
                "candidates": ["Option A", "Option B"],
                "score": 0.9
            }

        # Simulate Missing Corpus (Test Case A2/C1)
        if "missing" in q_lower or "abc999" in q_lower or "random" in q_lower:
             # If strictly missing corpus known topic
             if "asr920" in q_lower:
                 print("DEBUG: Returning Missing Corpus ASR920")
                 return {"match_type": "missing_corpus", "topic": "cisco asr920", "score": 1.0}
             return None # Just no match

        # Simulate Deterministic Matches
        if "ne8000" in q_lower and "config" in q_lower:
            print("DEBUG: Returning NE8000 Config")
            return self.articles["Huawei NE8000 Config"]
        if "ne8000" in q_lower and "overview" in q_lower:
             return self.articles["Huawei NE8000 Overview"]
        if "ne8000" in q_lower and "คืออะไร" in q_lower:
             return self.articles["Huawei NE8000 Overview"]
        if "577k" in q_lower and "แก้" in q_lower:
             return self.articles["Troubleshoot 577K"]
        if "cisco asr920" in q_lower:
             print("DEBUG: Returning Missing Corpus ASR920 (Broad)")
             return {"match_type": "missing_corpus", "topic": "cisco asr920", "score": 1.0}

        print("DEBUG: No Match Found")
        return None

    def find_links_fuzzy(self, query: str, threshold: float = 0.8) -> list:
        return []

    def find_best_phrase_match(self, query: str) -> Optional[Dict[str, Any]]:
        return None
        
    def get_article_content(self, url: str) -> str:
        # Find article text by url
        for k, v in self.articles.items():
            if v["url"] == url:
                return v["text"]
        return "Fake content"

# Mock dependencies
class MockVS:
    def hybrid_query(self, q, top_k, alpha=0.5, where=None):
        return []

class MockWebHandler:
    pass

class MockContentClassifier:
    def classify(self, **kwargs):
        return {
            "should_summarize": True,
            "content_type": "TEXT_ARTICLE"
        }

class MockLLM:
    def complete(self, prompt, **kwargs):
        return "Mock LLM Summary"
    def chat(self, messages, **kwargs):
        return "Mock LLM Answer"
    def predict(self, prompt, **kwargs):
        return "Mock LLM Prediction"

# Mock clean_html_to_text
import src.ingest.clean
class MockCleanResult:
    def __init__(self, text):
        self.text = text

def mock_clean_html_to_text(html):
    return MockCleanResult(html)

src.ingest.clean.clean_html_to_text = mock_clean_html_to_text

# =============================================================================
# TEST RUNNER
# =============================================================================

def setup_engine():
    cfg = {
        "llm": {"model": "mock", "base_url": "mock"},
        "chat": {"show_context": False},
        "rag": {"use_cache": False},
        "security": {"hardening_threshold": 0.8},
        "retrieval": {"top_k": 3}
    }
    engine = ChatEngine(cfg)
    engine.processed_cache = FakeProcessedCache()
    engine.vs = MockVS()
    engine.web_handler = MockWebHandler()
    engine.content_classifier = MockContentClassifier()
    engine.llm = MockLLM()
    engine.load_records = lambda x: [] # Mock legacy lookup
    return engine

RESULTS = []

def run_test(name, query, expected_checks):
    engine = setup_engine()
    print(f"\n--- RUNNING: {name} ---")
    print(f"Query: '{query}'")
    
    start_t = time.time()
    res = engine.process(query)
    duration = time.time() - start_t
    
    failures = []
    
    # Check 1: Route/Intent
    if "expected_route" in expected_checks:
        if res.get("route") != expected_checks["expected_route"]:
            failures.append(f"Route Mismatch: Expected {expected_checks['expected_route']}, Got {res.get('route')}")

    if "expected_intent" in expected_checks:
        # Intent is usually internal, but checked via block reason or answer content
        # We can check engine._classify_intent if we want, but checking output is better
        pass
        
    if "blocked" in expected_checks and expected_checks["blocked"]:
        if "blocked" not in res.get("route", "") and "rag_missing" not in res.get("route", ""):
            failures.append(f"Failed to BLOCK. Route was: {res.get('route')}")

    if "block_reason" in expected_checks:
        if res.get("block_reason") != expected_checks["block_reason"]:
             failures.append(f"Block Reason Mismatch: Expected {expected_checks['block_reason']}, Got {res.get('block_reason')}")

    status = "PASS" if not failures else "FAIL"
    RESULTS.append({
        "name": name,
        "query": query,
        "status": status,
        "route": res.get("route"),
        "failures": failures,
        "duration": duration
    })
    
    if status == "FAIL":
        print(f"❌ FAIL: {failures}")
    else:
        print(f"✅ PASS")

# =============================================================================
# TEST DEFINITIONS
# =============================================================================

def run_all_tests():
    # SET A: INTENT CLASSIFICATION
    run_test("A1: Huawei NE8000 config BGP", "Huawei NE8000 config BGP", {
        "expected_route": "article_answer", # Deterministic match
    })
    
    run_test("A2: Cisco ASR920 command (Missing)", "Cisco ASR920 command", {
        "expected_route": "rag_missing_corpus",
        "blocked": True
    })

    run_test("A3: Overview Concept", "Huawei NE8000 คืออะไร", {
        "expected_route": "article_answer"
    })
    
    run_test("A4: Troubleshooting", "Huawei 577K SNR ต่ำ แก้ไข", {
         "expected_route": "article_answer"
    })

    # SET B: SCOPE ENFORCEMENT
    run_test("B1: Technical Query Web Block", "Config Huawei NE8000", {
        "expected_route": "article_answer" # Should match deterministic, NOT web
    })
    
    run_test("B2: External Knowledge Attempt (Best Practice)", "Huawei NE8000 best practice", {
        # If "best practice" matches "opinion" or triggers OUT_OF_SCOPE?
        # "best" is in blocklist? Let's assume so or check logic
        # If not, it falls through to missing NO_MATCH or Web Blocked
        "blocked": True 
    })
    
    run_test("B3: Vendor Comparison", "Huawei NE8000 vs Cisco ASR920", {
        "expected_route": "blocked_scope",
        "block_reason": "OUT_OF_SCOPE_QUERY",
        "blocked": True
    })

    # SET C: REVIEWER MODE
    run_test("C1: Random Model", "Huawei ABC999 config", {
         "expected_route": "rag_miss_coverage",
         # "blocked": True # Not strictly blocked unless alias found
    })
    
    run_test("C2: Partial Model Name", "Huawei NE8", {
         "expected_route": "rag_miss_coverage",
         # "blocked": True
    })

    # Intent Mismatch Test (My addition based on implementation)
    run_test("C_Extra: Intent Mismatch", "Huawei NE8000 Overview", {
        # Querying overview for overview article -> OK
        "expected_route": "article_answer"
    })
    # Real mismatch: Query "Config" but get "Overview" handle?
    # We need a query that classifies as CONFIG but matches OVERVIEW article
    # Query: "Huawei NE8000 Overview command" -> Intent CONFIG (keyword 'command')
    # Article: "Huawei NE8000 Overview" (Type OVERVIEW)
    # This should BLOCK
    # BUT ProcessedCache needs to return Overview article for this query.
    # My FakeProcessedCache logic: if "ne8000" and "overview" -> returns Overview article.
    run_test("C_Extra: Mismatch Config vs Overview", "Huawei NE8000 Overview command", {
         "expected_route": "blocked_intent",
         "block_reason": "INTENT_MISMATCH"
    })

    run_test("C4: Ambiguous Intent", "Ambiguous Query", {
        "expected_route": "blocked_ambiguous",
        "blocked": True
    })

    # SET D: RESPONSE MODE
    # D1 is covered by A1
    # D3 is covered by A2
    
def print_report():
    print("\n" + "="*60)
    print("SMC GOVERNANCE COMPLIANCE REPORT")
    print("="*60)
    
    passed = len([r for r in RESULTS if r["status"] == "PASS"])
    total = len(RESULTS)
    
    for r in RESULTS:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{icon} {r['name'].ljust(40)} | Route: {r.get('route', 'N/A')}")
        if r["status"] == "FAIL":
            for f in r["failures"]:
                print(f"   └─ {f}")
    
    print("-" * 60)
    print(f"TOTAL: {total} | PASS: {passed} | FAIL: {total - passed}")
    print("="*60)
    if passed == total:
        print("RESULT: GO FOR PHASE 6.5")
    else:
        print("RESULT: NO-GO")

if __name__ == "__main__":
    try:
        run_all_tests()
        print_report()
    except Exception as e:
        print(f"CRITICAL EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()
