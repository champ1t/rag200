#!/usr/bin/env python3
"""
Test Contact Precision Logic
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.contact_precision import is_valid_contact_query

# Test cases
test_cases = [
    # Valid CONTACT queries
    ("เบอร์ OMC", True, "Explicit phone number request"),
    ("เบอร์ติดต่อ FTTx", True, "Contact number request"),
    ("ติดต่อช่าง", True, "Contact person request"),
    ("โทรหา HelpDesk", True, "Call someone request"),
    
    # INVALID CONTACT queries (technical/config)
    ("เปิดโทร 3 สาย บน ONU", False, "Configuration query"),
    ("โทรได้กี่สาย", False, "Capacity query"),
    ("ตั้งค่าโทร", False, "Configuration query"),
    ("config IP Phone", False, "Technical config"),
    ("SIP proxy", False, "Technical system"),
    ("โทรภายใน", False, "Internal calling feature"),
    ("เปิดโทร 2 สาย", False, "Line configuration"),
]

print("=== Contact Precision Test ===\n")

passed = 0
failed = 0

for query, expected, description in test_cases:
    result = is_valid_contact_query(query)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {query}")
    print(f"  Expected: {'CONTACT' if expected else 'NOT_CONTACT'}")
    print(f"  Got: {'CONTACT' if result else 'NOT_CONTACT'}")
    print(f"  Description: {description}")
    print()

print(f"Results: {passed} passed, {failed} failed")
