#!/usr/bin/env python3
"""Test vendor/model extraction logic"""
import sys
import os
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

# Test cases
test_cases = [
    ("Huawei NE8000 command", "huawei", "ne8000"),
    ("Cisco ASR920 config", "cisco", "asr920"),
    ("ZTE C300 basic command", "zte", "c300"),
    ("config vlan cisco", "cisco", ""),
    ("Huawei 577K troubleshooting", "huawei", "577k"),
    ("Basic command OLT ZTE C300", "zte", "c300"),
]

print("Testing vendor/model extraction...")
print("=" * 60)

cache = ProcessedCache()

for query, expected_vendor, expected_model in test_cases:
    vendor, model = cache._extract_vendor_model(query)
    status = "✅" if (vendor == expected_vendor and model == expected_model) else "❌"
    print(f"{status} Query: '{query}'")
    print(f"   Expected: vendor='{expected_vendor}', model='{expected_model}'")
    print(f"   Got:      vendor='{vendor}', model='{model}'")
    print()

print("=" * 60)
print("Testing complete!")
