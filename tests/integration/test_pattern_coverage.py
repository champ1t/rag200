#!/usr/bin/env python3
"""
Test: Pattern Coverage for Follow-up Detection

Verifies that common Thai follow-up patterns are detected.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.context import context_manager
import time

print("=" * 70)
print("Pattern Coverage Test")
print("=" * 70)

# Mock context
mock_context = {
    "entities": {"หาดใหญ่": "LOCATION", "OMC": "ORGANIZATION"},
    "intent": "CONTACT_LOOKUP",
    "timestamp": time.time(),
    "route": "contact_ambiguous"
}

# Test patterns
test_cases = [
    ("ขอเบอร์", True, "Basic contact request"),
    ("ของ RNOC ละ", True, "Continuation with ละ"),
    ("RNOC ล่ะ", True, "Continuation with ล่ะ"),
    ("อีกคน", True, "Another person"),
    ("อันนี้", True, "This one"),
    ("โทรอะไร", True, "Phone number request"),
    ("1", True, "Selection number (short)"),
    ("อธิบายหน่อย", True, "Request explanation"),
    ("ศูนย์ภูเก็ต", False, "New specific query (should NOT use context)"),
    ("show me config", False, "Completely different topic"),
]

results = []
for query, expected, description in test_cases:
    detected = context_manager.should_use_context(query, mock_context)
    passed = detected == expected
    status = "✅" if passed else "❌"
    results.append((query, expected, detected, passed, description))
    print(f"{status} '{query}' | Expected: {expected}, Got: {detected} | {description}")

print("\n" + "=" * 70)
total = len(results)
passed_count = sum(1 for _, _, _, p, _ in results if p)
print(f"Results: {passed_count}/{total} ({100*passed_count//total}%)")
print("=" * 70)

if passed_count == total:
    print("✅ ALL TESTS PASSED")
    sys.exit(0)
else:
    print("❌ SOME TESTS FAILED")
    sys.exit(1)
