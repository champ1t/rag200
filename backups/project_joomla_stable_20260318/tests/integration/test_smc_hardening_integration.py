#!/usr/bin/env python3
"""
SMC Hardening Integration Tests
Tests all critical scenarios from the implementation plan
"""
import sys
import os
import yaml

sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

# Load actual config for ChatEngine initialization
with open("configs/config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)



def print_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {name}")
    if details:
        print(f"  {details}")

def test_strict_vendor_matching():
    """Test Rule 3: MUST NOT match wrong vendor"""
    engine = ChatEngine(cfg=CONFIG)
    
    # Query for Huawei, should NOT return Cisco articles
    query = "Huawei NE8000 command"
    vendor, model = engine.processed_cache._extract_vendor_model(query)
    
    # Verify extraction
    passed = (vendor == "huawei" and model == "ne8000")
    print_test("Vendor/Model Extraction", passed, 
               f"vendor='{vendor}', model='{model}'")
    
    return passed

def test_strict_model_matching():
    """Test Rule 3: MUST NOT match wrong model"""
    cache = ChatEngine(cfg=CONFIG).processed_cache
    
    # Test that NE8000 doesn't match 577K
    query_vendor, query_model = cache._extract_vendor_model("Huawei NE## 8000")
    article_vendor, article_model = cache._extract_vendor_model("Huawei 577K")
    
    # These should be different models
    passed = query_model != article_model
    print_test("Model Distinction (NE8000 ≠ 577K)", passed,
               f"query_model='{query_model}', article_model='{article_model}'")
    
    return passed

def test_technical_query_detection():
    """Test that technical queries are detected correctly"""
    engine = ChatEngine(cfg=CONFIG)
    
    test_cases = [
        ("Huawei NE8000 command", True),
        ("Cisco ASR920 config", True),
        ("ZTE C300 basic", True),
        ("What is HTTP?", False),
        ("How to configure vlan", False),
    ]
    
    all_passed = True
    for query, expected in test_cases:
        result = engine._has_vendor_model_pattern(query)
        passed = (result == expected)
        if not passed:
            print_test(f"Technical Detection: '{query}'", passed,
                      f"expected={expected}, got={result}")
            all_passed = False
    
    print_test("Technical Query Detection", all_passed)
    return all_passed

def test_title_fast_path():
    """Test that normalized title index was built"""
    cache = ChatEngine(cfg=CONFIG).processed_cache
    
    # Check that the index was populated
    passed = len(cache._normalized_title_index) > 0
    count = len(cache._normalized_title_index)
    
    print_test("Title Index Populated", passed,
               f"{count} normalized titles indexed")
    
    return passed

def test_missing_corpus_detection():
    """Test that known aliases without docs are detected"""
    cache = ChatEngine(cfg=CONFIG).processed_cache
    
    # Test a known missing alias (from audit)
    result = cache.find_best_article_match("cisco asr920")
    
    passed = (result and result.get("match_type") == "missing_corpus")
    print_test("Missing Corpus Detection (ASR920)", passed,
               f"result type: {result.get('match_type') if result else 'None'}")
    
    return passed

def test_existing_article_match():
    """Test that existing articles are still found correctly"""
    cache = ChatEngine(cfg=CONFIG).processed_cache
    
    # Test a known existing article
    result = cache.find_best_article_match("huawei ne8000")
    
    passed = (result and result.get("match_type") == "deterministic")
    if result:
        print_test("Article Match (NE8000)", passed,
                   f"title: {result.get('title', 'N/A')[:50]}...")
    else:
        print_test("Article Match (NE8000)", False, "No result returned")
    
    return passed

def main():
    print("=" * 70)
    print("SMC HARDENING INTEGRATION TESTS")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Strict Vendor Matching", test_strict_vendor_matching()))
    results.append(("Strict Model Matching", test_strict_model_matching()))
    results.append(("Technical Query Detection", test_technical_query_detection()))
    results.append(("Title Fast Path", test_title_fast_path()))
    results.append(("Missing Corpus Detection", test_missing_corpus_detection()))
    results.append(("Existing Article Match", test_existing_article_match()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
