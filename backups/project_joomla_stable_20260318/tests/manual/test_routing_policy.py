#!/usr/bin/env python3
"""
Test Routing Policy
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.routing_policy import RoutingPolicy

# Test cases
test_cases = [
    # ASSET_LOOKUP (table + technical)
    ("ขอดูตาราง proxy ip phone", "ASSET_LOOKUP", "Table + technical entities"),
    ("ตาราง VLAN", "ASSET_LOOKUP", "Table + VLAN"),
    ("รายการ ONU", "ASSET_LOOKUP", "List + ONU"),
    ("show IP Phone config", "ASSET_LOOKUP", "Show + config"),
    ("config SIP proxy", "ASSET_LOOKUP", "Config + SIP"),
    
    # CONTACT_LOOKUP
    ("เบอร์ OMC", "CONTACT_LOOKUP", "Contact request"),
    ("ติดต่อช่าง", "CONTACT_LOOKUP", "Contact person"),
    
    # TEAM_LOOKUP
    ("ทีม FTTx", "TEAM_LOOKUP", "Team request"),
    ("หน่วยงานดูแล ONU", "TEAM_LOOKUP", "Unit responsible"),
    
    # ARTICLE_SEARCH (fallback)
    ("วิธีแก้ปัญหา ONU", "ARTICLE_SEARCH", "How-to without table"),
    ("ข้อจำกัดของ NCS", "ARTICLE_SEARCH", "General query"),
]

print("=== Routing Policy Test ===\n")

passed = 0
failed = 0

for query, expected, description in test_cases:
    result = RoutingPolicy.route(query)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {query}")
    print(f"  Expected: {expected}")
    print(f"  Got: {result}")
    print(f"  Description: {description}")
    print()

print(f"Results: {passed} passed, {failed} failed\n")

# Test fallback logic
print("=== Fallback Logic Test ===\n")
fallback_tests = [
    ("ASSET_LOOKUP", "asset_miss", True, "Asset miss → fallback"),
    ("TEAM_LOOKUP", "team_miss", True, "Team miss → fallback"),
    ("CONTACT_LOOKUP", "contact_hit", False, "Contact hit → no fallback"),
]

for route, result, expected, description in fallback_tests:
    should_fallback = RoutingPolicy.should_fallback_to_article(route, result)
    status = "✓ PASS" if should_fallback == expected else "✗ FAIL"
    
    print(f"{status} | {route} + {result}")
    print(f"  Expected: {'FALLBACK' if expected else 'NO_FALLBACK'}")
    print(f"  Got: {'FALLBACK' if should_fallback else 'NO_FALLBACK'}")
    print(f"  Description: {description}")
    print()

# Test not-found response
print("\n=== Not-Found Response Test ===\n")
query = "ขอดูตาราง proxy ip phone"
response = RoutingPolicy.format_not_found_response(query, "ASSET_LOOKUP")
print(f"Query: {query}")
print(f"Response:\n{response}")
