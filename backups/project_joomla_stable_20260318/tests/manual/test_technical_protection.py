#!/usr/bin/env python3
"""
Test Technical Term Protection Logic
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.technical_protection import (
    has_protected_term,
    has_table_indicator,
    is_asset_table_query,
    safe_normalize
)

# Test cases
test_cases = [
    # ASSET_TABLE queries
    ("ขอดูตารางproxy ipphone", True, "Table + proxy + ipphone"),
    ("ตาราง VLAN", True, "Table + VLAN"),
    ("รายการ ONU", True, "List + ONU"),
    ("show IP Phone config", True, "Show + IP Phone"),
    
    # NOT ASSET_TABLE (no table indicator)
    ("เปิดโทร 3 สาย บน ONU", False, "Config query, no table"),
    ("เบอร์ OMC", False, "Contact query"),
    
    # Protected term detection
    ("ipphone config", "ipphone", "Has ipphone"),
    ("proxy sip", "proxy", "Has proxy"),
    ("VLAN planning", "vlan", "Has VLAN"),
]

print("=== Technical Protection Test ===\n")

print("## ASSET_TABLE Detection\n")
for query, expected, description in test_cases[:6]:
    result = is_asset_table_query(query)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    print(f"{status} | {query}")
    print(f"  Expected: {'ASSET_TABLE' if expected else 'NOT_ASSET_TABLE'}")
    print(f"  Got: {'ASSET_TABLE' if result else 'NOT_ASSET_TABLE'}")
    print(f"  Description: {description}")
    print()

print("\n## Protected Term Detection\n")
for query, expected_term, description in test_cases[6:]:
    has_term = has_protected_term(query)
    status = "✓ PASS" if has_term else "✗ FAIL"
    
    print(f"{status} | {query}")
    print(f"  Expected term: {expected_term}")
    print(f"  Has protected term: {has_term}")
    print(f"  Description: {description}")
    print()

print("\n## Safe Normalization\n")
norm_tests = [
    ("ขอดูตารางproxy ipphone", "ขอดูตารางproxy ip phone"),
    ("ip-phone config", "ip phone config"),
    ("  multiple   spaces  ", "multiple spaces"),
]

for original, expected in norm_tests:
    result = safe_normalize(original)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    print(f"{status} | '{original}'")
    print(f"  Expected: '{expected}'")
    print(f"  Got: '{result}'")
    print()
