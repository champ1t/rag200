#!/usr/bin/env python3
"""
Test Fail-Soft Reroute Logic
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.failsoft_reroute import should_reroute_to_howto, get_reroute_intent

# Test cases
test_cases = [
    # Should REROUTE (technical + config verb + miss)
    ("เปิดโทร 3 สาย บน ONU", "contact_miss_strict", True, "Technical config query"),
    ("ตั้งค่า IP Phone", "team_miss", True, "IP Phone configuration"),
    ("ดู config Router", "contact_miss_strict", True, "View router config"),
    ("แก้ VLAN", "team_miss", True, "Fix VLAN"),
    ("คำสั่ง OLT", "contact_miss_strict", True, "OLT commands"),
    
    # Should NOT REROUTE (not a miss)
    ("เปิดโทร 3 สาย", "team_hit", False, "Not a miss"),
    
    # Should NOT REROUTE (no technical entity)
    ("ติดต่อช่าง", "contact_miss_strict", False, "No technical entity"),
    
    # Should NOT REROUTE (no config verb)
    ("ONU ของเรา", "team_miss", False, "No config verb"),
]

print("=== Fail-Soft Reroute Test ===\n")

passed = 0
failed = 0

for query, route, expected, description in test_cases:
    result = should_reroute_to_howto(query, route)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {query}")
    print(f"  Route: {route}")
    print(f"  Expected: {'REROUTE' if expected else 'NO_REROUTE'}")
    print(f"  Got: {'REROUTE' if result else 'NO_REROUTE'}")
    print(f"  Description: {description}")
    
    # Test get_reroute_intent
    if result:
        new_intent = get_reroute_intent(query, "CONTACT_LOOKUP", route)
        print(f"  New Intent: {new_intent}")
    
    print()

print(f"Results: {passed} passed, {failed} failed")
