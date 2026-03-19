#!/usr/bin/env python3
"""
Comprehensive Test: Complete Context Memory (All Features)

Tests:
1. Basic context save/load
2. Intent compatibility check
3. Multi-entity selection
4. Cross-domain blocking
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

import yaml
from pathlib import Path

print("=" * 70)
print("Context Memory - Comprehensive Test (All Features)")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

print("\n✅ ChatEngine loaded\n")

test_results = []

# =========================================================================
# Test 1: Basic Context Save/Load (Same as before)
# =========================================================================
print("=" * 70)
print("Test 1: Basic Context (ศูนย์หาดใหญ่โทรอะไร → ขอเบอร์)")
print("=" * 70)

engine.clear_session("test1")
result1 = engine.process("ศูนย์หาดใหญ่โทรอะไร")
print(f"\nQ1 Route: {result1.get('route')}")

context_saved = engine.last_context is not None
if context_saved:
    print(f"✅ Context saved")
    print(f"  Entities: {engine.last_context.get('entities', {})}")
    print(f"  Intent: {engine.last_context.get('intent')}")
    
result2 = engine.process("ขอเบอร์")
print(f"\nQ2 Route: {result2.get('route')}")

test1_pass = "หาดใหญ่" in result2.get('answer', '') or "OMC" in result2.get('answer', '')
test_results.append(("Basic Context", test1_pass))
print(f"\n{'✅ PASS' if test1_pass else '❌ FAIL'}")

# =========================================================================
# Test 2: Intent Compatibility Check (CONTACT → TECH should block)
# =========================================================================
print("\n" + "=" * 70)
print("Test 2: Intent Compatibility (CONTACT context, TECH query)")
print("=" * 70)

engine.clear_session("test1")
# Set contact context
result_contact = engine.process("ขอเบอร์ OMC")
print(f"\nQ1: CONTACT query, Route: {result_contact.get('route')}")

# Try tech query (should NOT use contact context)
result_tech = engine.process("คำสั่งอะไรบ้าง")
print(f"\nQ2: TECH query after CONTACT, Route: {result_tech.get('route')}")

# Should NOT have OMC in tech answer (context blocked)
test2_pass = "OMC" not in result_tech.get('answer', '')
if engine.last_context:
    print(f"  Last Intent: {engine.last_context.get('intent')}")
test_results.append(("Intent Compatibility", test2_pass))
print(f"\n{'✅ PASS - Context blocked' if test2_pass else '❌ FAIL - Context leaked'}")

# =========================================================================
# Test 3: Multi-Entity Smart Selection
# =========================================================================
print("\n" + "=" * 70)
print("Test 3: Multi-Entity Selection (Should pick LOCATION for contact)")
print("=" * 70)

engine.clear_session("test1")
# Create context with multiple entities
from src.context import context_manager
engine.last_context = {
    "entities": {
        "หาดใหญ่": "LOCATION",
        "OMC": "ORGANIZATION", 
        "OLT": "DEVICE"
    },
    "intent": "CONTACT_LOOKUP",
    "timestamp": 1234567890,
    "route": "contact_hit"
}

# Contact query should prefer LOCATION
result_multi = engine.process("ขอเบอร์")
print(f"\nRoute: {result_multi.get('route')}")
print(f"Answer preview: {result_multi.get('answer', '')[:150]}")

# Should have หาดใหญ่ (LOCATION priority for contact queries)
test3_pass = "หาดใหญ่" in result_multi.get('answer', '')
test_results.append(("Multi-Entity Selection", test3_pass))
print(f"\n{'✅ PASS - LOCATION selected' if test3_pass else '❌ FAIL'}")

# =========================================================================
# Test 4: Context Expiration (Simulate)
# =========================================================================
print("\n" + "=" * 70)
print("Test 4: Context Not Expired (Fresh context)")
print("=" * 70)

import time
engine.clear_session("test1")
engine.last_context = {
    "entities": {"หาดใหญ่": "LOCATION"},
    "intent": "CONTACT_LOOKUP",
    "timestamp": time.time(),  # Fresh
    "route": "contact_hit"
}

result_fresh = engine.process("ขอเบอร์")
test4_pass = "หาดใหญ่" in result_fresh.get('answer', '')
test_results.append(("Context Fresh", test4_pass))
print(f"\n{'✅ PASS - Context used' if test4_pass else '❌ FAIL'}")

# =========================================================================
# Summary
# =========================================================================
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

for test_name, passed in test_results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")

total_passed = sum(1 for _, p in test_results if p)
total_tests = len(test_results)
score = (total_passed / total_tests) * 100

print(f"\nScore: {total_passed}/{total_tests} ({score:.0f}%)")
print("=" * 70)

success = total_passed == total_tests
sys.exit(0 if success else 1)
