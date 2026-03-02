"""
Test Ambiguity Detector - Step 5
Tests heuristic rules for detecting ambiguous queries.
"""

import sys
import os
sys.path.append(os.getcwd())

from src.query_analysis.ambiguity_detector import check_ambiguity

def test_ambiguity_detector():
    print("🧪 Testing Ambiguity Detector (Step 5)\n")
    print("="*70)
    
    test_cases = [
        # === Ambiguous queries (should trigger clarification) ===
        {
            "query": "คำสั่งHuawei",
            "should_be_ambiguous": True,
            "expected_reason": "BROAD_VENDOR_COMMAND"
        },
        {
            "query": "Huawei command",
            "should_be_ambiguous": True,
            "expected_reason": "BROAD_VENDOR_COMMAND"
        },
        {
            "query": "ZTE commands",
            "should_be_ambiguous": True,
            "expected_reason": "BROAD_VENDOR_COMMAND"
        },
        {
            "query": "Huawei",
            "should_be_ambiguous": True,
            "expected_reason": "VENDOR_ONLY"
        },
        {
            "query": "รวมคำสั่ง ZTE",
            "should_be_ambiguous": True,
            "expected_reason": "INDEX_QUERY"
        },
        
        # === Specific queries (should pass through) ===
        {
            "query": "Huawei add vlan",
            "should_be_ambiguous": False,
            "expected_reason": None
        },
        {
            "query": "ZTE show interface",
            "should_be_ambiguous": False,
            "expected_reason": None
        },
        {
            "query": "Huawei OLT config",
            "should_be_ambiguous": False,
            "expected_reason": None
        },
        {
            "query": "ZTE-SW Command",  # Exact match case
            "should_be_ambiguous": False,
            "expected_reason": None
        },
        {
            "query": "OLT คืออะไร",
            "should_be_ambiguous": False,
            "expected_reason": None
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for tc in test_cases:
        query = tc["query"]
        expected_ambiguous = tc["should_be_ambiguous"]
        expected_reason = tc["expected_reason"]
        
        print(f"\nQuery: '{query}'")
        
        result = check_ambiguity(query)
        
        is_ambiguous = result["is_ambiguous"]
        reason = result["reason"]
        suggestion = result.get("suggestion")
        
        print(f"  Ambiguous: {is_ambiguous}")
        print(f"  Reason: {reason}")
        if suggestion:
            print(f"  Suggestion: {suggestion}")
        
        # Validate
        if is_ambiguous == expected_ambiguous:
            if expected_reason is None or reason == expected_reason:
                print("  ✅ PASS")
                passed += 1
            else:
                print(f"  ❌ FAIL - Expected reason: {expected_reason}, got: {reason}")
        else:
            print(f"  ❌ FAIL - Expected ambiguous: {expected_ambiguous}, got: {is_ambiguous}")
    
    print("\n" + "="*70)
    print(f"📊 Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(test_ambiguity_detector())
