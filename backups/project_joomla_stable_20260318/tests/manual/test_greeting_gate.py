#!/usr/bin/env python3
"""
Test Greeting Gate Logic
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.greeting_gate import is_pure_greeting, get_greeting_response

# Test cases
test_cases = [
    # PURE GREETINGS
    ("สวัสดีครับ", True, "Pure Thai greeting"),
    ("สวัสดี", True, "Pure Thai greeting (short)"),
    ("hi", True, "Pure English greeting"),
    ("hello", True, "Pure English greeting"),
    ("ดีครับ", True, "Pure Thai greeting variant"),
    ("ดีจ้า", True, "Pure Thai greeting casual"),
    ("👋", True, "Pure emoji greeting"),
    ("hi 👋", True, "Greeting + emoji"),
    
    # NOT PURE GREETINGS (has question/request)
    ("สวัสดีครับ ขอเบอร์ OMC", False, "Greeting + question"),
    ("hi, ขอดูตาราง VLAN", False, "Greeting + request"),
    ("hello how are you doing today", False, "Too long"),
    ("เบอร์ OMC", False, "No greeting token"),
    ("ขอดูตารางproxy ipphone", False, "No greeting"),
    
    # Edge cases
    ("", False, "Empty string"),
    ("สวัสดีครับ พี่", False, "Greeting + address (has content)"),
]

print("=== Greeting Gate Test ===\n")

passed = 0
failed = 0

for query, expected, description in test_cases:
    result = is_pure_greeting(query)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | '{query}'")
    print(f"  Expected: {'PURE_GREETING' if expected else 'NOT_GREETING'}")
    print(f"  Got: {'PURE_GREETING' if result else 'NOT_GREETING'}")
    print(f"  Description: {description}")
    print()

print(f"Results: {passed} passed, {failed} failed\n")

# Test greeting response
print("=== Greeting Response ===")
print(get_greeting_response())
