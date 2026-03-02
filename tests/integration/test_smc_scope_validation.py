
import sys
import os
import json
import time
from typing import Dict, Any, Optional

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
import src.chat_engine
import src.ingest.clean

# =============================================================================
# MOCK INFRASTRUCTURE (Adapted from test_smc_governance_validation.py)
# =============================================================================

class MockFetchResult:
    def __init__(self, content):
        self.status_code = 200
        self.text = content
        self.page_content = content
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
            "asr920": ["cisco asr920"], # Known alias, but will be missing content
            "jun-mx960": ["juniper mx960"] # Add Juniper to verify "Known alias but missing" vs "Unknown"
        }
        self.articles = {}

    def normalize_for_matching(self, s):
        return s.lower().strip()

    def find_best_article_match(self, query, threshold=None):
        q_lower = query.lower()
        
        # 1. Simulate MISSING CORPUS for Cisco ASR920
        if "asr920" in q_lower:
             return {"match_type": "missing_corpus", "topic": "cisco asr920", "score": 1.0}
        
        # 2. Simulate MISSING for Juniper (Not in SMC)
        if "juniper" in q_lower:
            # If we defined it in aliases, it returns missing_corpus
            return {"match_type": "missing_corpus", "topic": "juniper mx960", "score": 1.0}

        return None # No match found

    def find_links_fuzzy(self, keyword, threshold=None):
        return []

    def find_best_phrase_match(self, query):
        return None

    def get_article_content(self, url):
        return None

class MockVS:
    def hybrid_query(self, text, top_k=3, alpha=0.5, where=None):
        return [] # Return EMPTY to simulate "No Info in SMC"

class MockWebHandler:
    def run_search(self, query, **kwargs):
        return "WEB_SEARCH_RESULT_FORBIDDEN"

class MockContentClassifier:
    def predict(self, prompt, **kwargs):
        return "GENERAL_QA" # Default

class MockLLM:
    def predict(self, prompt, **kwargs):
        return "Mock LLM Response"

# =============================================================================
# TEST RUNNER
# =============================================================================

def setup_engine():
    cfg = {
        "llm": {"model": "mock", "base_url": "mock"},
        "chat": {"show_context": False},
        "rag": {"use_cache": False},
        "security": {"hardening_threshold": 0.8}, # Strict threshold
        "retrieval": {"top_k": 3}
    }
    engine = ChatEngine(cfg)
    engine.processed_cache = FakeProcessedCache()
    engine.vs = MockVS()
    engine.web_handler = MockWebHandler()
    engine.content_classifier = MockContentClassifier()
    engine.llm = MockLLM()
    engine.load_records = lambda x: []
    return engine

def run_test(name, query, expected_outcomes):
    print(f"\n--- RUNNING: {name} ---")
    print(f"Query: '{query}'")
    
    start_time = time.time()
    try:
        engine = setup_engine()
        response = engine.process(query, session_id="test_scope_val")
        
        route = response.get("route", "unknown")
        answer = response.get("answer", "")
        
        print(f"Route: {route}")
        
        # Verification
        failed = False
        reasons = []
        
        expected_route = expected_outcomes.get("expected_route")
        if expected_route and route != expected_route:
            # Allow rag_miss_coverage or rag_no_match or rag_missing_corpus or rag_no_docs as "BLOCK" equivalents
            allowed_blocks = ["rag_miss_coverage", "rag_no_match", "rag_missing_corpus", "blocked_scope", "blocked_intent", "rag_no_docs"]
            is_blocked = route in allowed_blocks
            
            if expected_outcomes.get("expect_blocking") and is_blocked:
                pass # OK, it was blocked
            else:
                reasons.append(f"Route Mismatch: Expected {expected_route}, Got {route}")
                failed = True

        if expected_outcomes.get("forbidden_terms"):
            for term in expected_outcomes["forbidden_terms"]:
                if term in answer:
                    reasons.append(f"Forbidden Term Found: '{term}'")
                    failed = True
                    
        # Check strict 0 web calls (Verified by MockWebHandler returning a distinct string if called, 
        # but since we mock ChatEngine logic, we rely on route not being 'web_search')
        if route == "web_search":
             reasons.append("CRITICAL FAIL: Web Search was triggered!")
             failed = True

        if failed:
            print(f"❌ FAIL: {reasons}")
            return False
        else:
            print("✅ PASS")
            return True
            
    except Exception as e:
        print(f"❌ CRASH: {e}")
        import traceback
        traceback.print_exc()
        return False

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    tests = [
        {
            "name": "Case 1: Unknown Vendor/Model (Not in SMC)",
            "query": "Juniper MX960 config",
            "expect": {
                "expected_route": "rag_missing_corpus", # Or rag_miss_coverage
                "expect_blocking": True
            }
        },
        {
            "name": "Case 2: General Knowledge (Not SMC)",
            "query": "What is BGP protocol?",
            "expect": {
                "expected_route": "rag_miss_coverage", # Should fail to find documents
                "expect_blocking": True
            }
        },
        {
            "name": "Case 3: Cross-Vendor Mix (Hard Block)",
            "query": "Huawei NE8000 vs Cisco ASR920 configuration",
            "expect": {
                "expected_route": "blocked_scope",
                "expect_blocking": True
            }
        }
    ]
    
    total = 0
    passed = 0
    
    print("============================================================")
    print("SMC SCOPE VALIDATION (STEP 0)")
    print("============================================================")
    
    for t in tests:
        total += 1
        if run_test(t["name"], t["query"], t["expect"]):
            passed += 1
            
    print("\n============================================================")
    print(f"TOTAL: {total} | PASS: {passed} | FAIL: {total - passed}")
    print("============================================================")
    
    if passed == total:
        print("RESULT: GO FOR PHASE 3")
        sys.exit(0)
    else:
        print("RESULT: NO-GO (Fix Scope First)")
        sys.exit(1)
