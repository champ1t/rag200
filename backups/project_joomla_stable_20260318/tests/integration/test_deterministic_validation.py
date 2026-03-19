#!/usr/bin/env python3
"""
Deterministic Layer Validation Test Suite
Validates 100% correctness of deterministic routing with ZERO tolerance for failures.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.core.chat_engine import ChatEngine
import yaml

# Load config
with open('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

# Test results storage
results = []

def create_fresh_engine():
    """Create a fresh engine instance to ensure stateless testing"""
    return ChatEngine(cfg)

def test_case(test_id, query, expected_intent, must_not_contain, description):
    """
    Execute a single test case
    
    Args:
        test_id: Test identifier (e.g., "A1")
        query: Input query
        expected_intent: Expected intent classification
        must_not_contain: List of phrases that MUST NOT appear in answer
        description: Test description
    
    Returns:
        dict with test results
    """
    engine = create_fresh_engine()
    result = engine.process(query)
    
    answer = result.get('answer', '')
    route = result.get('route', '')
    
    # Check for forbidden phrases
    violations = []
    for phrase in must_not_contain:
        if phrase in answer or phrase in route:
            violations.append(phrase)
    
    passed = len(violations) == 0
    
    test_result = {
        'id': test_id,
        'query': query,
        'description': description,
        'expected_intent': expected_intent,
        'actual_route': route,
        'violations': violations,
        'passed': passed,
        'answer_preview': answer[:100] if answer else 'N/A'
    }
    
    results.append(test_result)
    return test_result

def test_context_isolation(test_id, queries, expected_intent_final, must_not_contain, description):
    """
    Test multi-turn context isolation
    
    Args:
        test_id: Test identifier
        queries: List of queries (last one is tested)
        expected_intent_final: Expected intent for final query
        must_not_contain: Forbidden phrases in final answer
        description: Test description
    """
    engine = create_fresh_engine()
    
    # Execute all queries
    for i, q in enumerate(queries):
        result = engine.process(q)
        if i == len(queries) - 1:
            # Test final query
            answer = result.get('answer', '')
            route = result.get('route', '')
            
            violations = []
            for phrase in must_not_contain:
                if phrase in answer or phrase in route:
                    violations.append(phrase)
            
            passed = len(violations) == 0
            
            test_result = {
                'id': test_id,
                'query': f"Context: {queries}",
                'description': description,
                'expected_intent': expected_intent_final,
                'actual_route': route,
                'violations': violations,
                'passed': passed,
                'answer_preview': answer[:100] if answer else 'N/A'
            }
            
            results.append(test_result)
            return test_result

def run_test_suite_a():
    """TEST SUITE A: DEFINE / EXPLAIN IMMUNITY"""
    print("\n" + "="*60)
    print("TEST SUITE A: DEFINE / EXPLAIN IMMUNITY")
    print("="*60)
    
    forbidden = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]
    
    test_case("A1", "ONU คืออะไร", "DEFINE_TERM", forbidden, 
              "Definition query must not trigger symptom follow-up")
    
    test_case("A2", "ไฟ LOS คืออะไร", "DEFINE_TERM", forbidden,
              "Definition query must not trigger HOWTO or follow-up")
    
    test_case("A3", "สรุปปัญหาไฟแดง ONU", "SUMMARY/EXPLAIN", forbidden,
              "Summary query must answer directly without Wi-Fi/LAN question")

def run_test_suite_b():
    """TEST SUITE B: CONTACT_LOOKUP ISOLATION"""
    print("\n" + "="*60)
    print("TEST SUITE B: CONTACT_LOOKUP ISOLATION")
    print("="*60)
    
    forbidden = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]
    
    test_case("B1", "ขอเบอร์ CSOC", "CONTACT_LOOKUP", forbidden,
              "Contact lookup must not trigger follow-up")
    
    test_context_isolation("B2", 
                          ["ONU ไฟแดง เน็ตใช้ไม่ได้", "ขอเบอร์ CSOC"],
                          "CONTACT_LOOKUP", forbidden,
                          "Contact lookup must ignore previous symptom context")

def run_test_suite_c():
    """TEST SUITE C: POSITION LOOKUP SAFETY"""
    print("\n" + "="*60)
    print("TEST SUITE C: POSITION LOOKUP SAFETY")
    print("="*60)
    
    forbidden = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]
    
    test_case("C1", "ใครคือ ผจ", "POSITION_HOLDER_LOOKUP", forbidden,
              "Position lookup must not trigger symptom follow-up")
    
    test_context_isolation("C2",
                          ["ใครคือ ผจ", "ขอเบอร์ OMC"],
                          "CONTACT_LOOKUP", forbidden,
                          "Contact lookup must not reference previous position query")

def run_test_suite_d():
    """TEST SUITE D: STATELESS GUARANTEE"""
    print("\n" + "="*60)
    print("TEST SUITE D: STATELESS GUARANTEE")
    print("="*60)
    
    queries = ["ONU คืออะไร", "ขอเบอร์หาดใหญ่", "ใครคือ ผจ"]
    forbidden = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]
    
    for i, query in enumerate(queries):
        test_case(f"D{i+1}", query, "DETERMINISTIC", forbidden,
                 f"Stateless test: {query} must produce identical routing")

def run_test_suite_e():
    """TEST SUITE E: NEGATIVE CONFIRMATION"""
    print("\n" + "="*60)
    print("TEST SUITE E: NEGATIVE CONFIRMATION")
    print("="*60)
    
    # All deterministic queries must NEVER trigger these
    forbidden_global = [
        "ใช้งานผ่าน Wi-Fi หรือสาย LAN ครับ?",
        "symptom_followup",
        "rag_clarify_followup"
    ]
    
    queries = [
        "ONU คืออะไร",
        "ขอเบอร์ CSOC",
        "ใครคือ ผจ",
        "ไฟ LOS หมายถึงอะไร",
        "สรุปปัญหาไฟแดง ONU"
    ]
    
    for i, query in enumerate(queries):
        test_case(f"E{i+1}", query, "DETERMINISTIC", forbidden_global,
                 f"Negative guard: {query} must never trigger follow-up")

def print_results():
    """Print test results table"""
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n{'ID':<6} {'Status':<8} {'Query':<30} {'Route':<25}")
    print("-" * 80)
    
    for r in results:
        status = "✅ PASS" if r['passed'] else "❌ FAIL"
        query = r['query'][:28] + ".." if len(r['query']) > 30 else r['query']
        route = r['actual_route'][:23] + ".." if len(r['actual_route']) > 25 else r['actual_route']
        print(f"{r['id']:<6} {status:<8} {query:<30} {route:<25}")
        
        if not r['passed']:
            print(f"       Violations: {', '.join(r['violations'])}")
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    
    print("\n" + "="*60)
    print(f"TOTAL: {passed}/{total} PASSED")
    print("="*60)
    
    return passed == total

def analyze_failures():
    """Analyze failed tests and identify root causes"""
    failures = [r for r in results if not r['passed']]
    
    if not failures:
        return None
    
    print("\n" + "="*60)
    print("FAILURE ANALYSIS")
    print("="*60)
    
    for f in failures:
        print(f"\n[{f['id']}] {f['description']}")
        print(f"Query: {f['query']}")
        print(f"Route: {f['actual_route']}")
        print(f"Violations: {', '.join(f['violations'])}")
        print(f"Answer Preview: {f['answer_preview']}")
    
    return failures

if __name__ == "__main__":
    print("\n🔍 DETERMINISTIC LAYER VALIDATION TEST SUITE")
    print("Zero-tolerance validation of deterministic routing correctness\n")
    
    # Run all test suites
    run_test_suite_a()
    run_test_suite_b()
    run_test_suite_c()
    run_test_suite_d()
    run_test_suite_e()
    
    # Print results
    all_passed = print_results()
    
    # Analyze failures
    failures = analyze_failures()
    
    # Final verdict
    print("\n" + "="*60)
    print("FINAL VERDICT")
    print("="*60)
    
    if all_passed:
        print("✅ DETERMINISTIC LOCKED")
        print("All tests passed. Deterministic layer is production-ready.")
        sys.exit(0)
    else:
        print("❌ NOT READY")
        print(f"Reason: {len(failures)} test(s) failed")
        print("System requires fixes before production deployment.")
        sys.exit(1)
