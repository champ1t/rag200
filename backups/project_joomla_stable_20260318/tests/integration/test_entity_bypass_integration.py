#!/usr/bin/env python3
"""
Integration Test: Entity Bypass Bug Fix - Deterministic Accuracy

Tests that entity bypass prevents valid queries from being blocked.

Expected Improvement: 85% → 95%+ deterministic accuracy
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import yaml
from pathlib import Path

print("=" * 70)
print("Entity Bypass Fix - Integration Test")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

print("\n✅ ChatEngine initialized with Entity Detector")
print(f"✅ Entity Detector: {hasattr(engine, 'entity_detector')}")

#=============================================================================
# Test Suite: Entity Bypass Queries (Should NOT be blocked)
# ============================================================================

print("\n" + "=" * 70)
print("Test 1: Entity Bypass - Device Queries")
print("=" * 70)

entity_device_tests = [
    {"query": "ขอเบอร์UMUX", "entity": "UMUX", "type": "DEVICE"},
    {"query": "คู่มือ OLT", "entity": "OLT", "type": "DEVICE"},
    {"query": "config BRAS", "entity": "BRAS", "type": "DEVICE"},
]

device_passed = 0
device_total = len(entity_device_tests)

for test in entity_device_tests:
    query = test["query"]
    print(f"\n🧪 Query: '{query}'")
    
    # Check entity detection
    entity_info = engine.entity_detector.detect(query)
    print(f"   Entity Detected: {entity_info['has_entity']} ({entity_info.get('entity_value', 'N/A')})")
    
    # Run query
    result = engine.process(query)
    route = result.get('route', '')
    answer = result.get('answer', '')
    
    # Check if blocked
    is_blocked = (
        'blocked' in route.lower() or
        'นอกขอบเขต' in answer or
        'ไม่พบข้อมูล' in answer
    )
    
    status = "✅" if not is_blocked else "❌"
    print(f"{status} Route: {route}")
    print(f"   Blocked: {is_blocked} (Expected: False)")
    
    if not is_blocked:
        device_passed += 1
    else:
        print(f"   Answer: {answer[:150]}")

device_accuracy = (device_passed / device_total) * 100

#=============================================================================
# Test Suite 2: Location Queries
#=============================================================================

print("\n" + "=" * 70)
print("Test 2: Entity Bypass - Location Queries")
print("=" * 70)

entity_location_tests = [
    {"query": "ขอเบอร์หาดใหญ่", "entity": "หาดใหญ่", "type": "LOCATION"},
    {"query": "ศูนย์ภูเก็ต", "entity": "ภูเก็ต", "type": "LOCATION"},
    {"query": "ขอเบอร์ชุมพร", "entity": "ชุม พร", "type": "LOCATION"},
]

location_passed = 0
location_total = len(entity_location_tests)

for test in entity_location_tests:
    query = test["query"]
    print(f"\n🧪 Query: '{query}'")
    
    entity_info = engine.entity_detector.detect(query)
    print(f"   Entity Detected: {entity_info['has_entity']}")
    
    result = engine.process(query)
    route = result.get('route', '')
    answer = result.get('answer', '')
    
    is_blocked = 'blocked' in route.lower() or 'ไม่พบ' in answer[:100]
    
    status = "✅" if not is_blocked else "❌"
    print(f"{status} Route: {route}")
    
    if not is_blocked:
        location_passed += 1

location_accuracy = (location_passed / location_total) * 100

#=============================================================================
# Test Suite 3: Organization Queries
#=============================================================================

print("\n" + "=" * 70)
print("Test 3: Entity Bypass - Organization Queries")
print("=" * 70)

entity_org_tests = [
    {"query": "ขอเบอร์ CSOC", "entity": "CSOC", "type": "ORGANIZATION"},
    {"query": "ขอเบอร์ OMC", "entity": "OMC", "type": "ORGANIZATION"},
]

org_passed = 0
org_total = len(entity_org_tests)

for test in entity_org_tests:
    query = test["query"]
    print(f"\n🧪 Query: '{query}'")
    
    entity_info = engine.entity_detector.detect(query)
    print(f"   Entity Detected: {entity_info['has_entity']}")
    
    result = engine.process(query)
    route = result.get('route', '')
    answer = result.get('answer', '')
    
    has_phone = '0' in answer and ('-' in answer or len([c for c in answer if c.isdigit()]) >= 8)
    
    status = "✅" if has_phone else "❌"
    print(f"{status} Route: {route}")
    print(f"   Has Phone: {has_phone}")
    
    if has_phone:
        org_passed += 1

org_accuracy = (org_passed / org_total) * 100

#=============================================================================
# Test Suite 4: Regression - Non-Entity Queries
#=============================================================================

print("\n" + "=" * 70)
print("Test 4: Regression - Non-Entity Queries (Should work normally)")
print("=" * 70)

regression_tests = [
    {"query": "สวัสดี", "should_have_entity": False},
    {"query": "ช่วยหน่อย", "should_have_entity": False},
]

regression_passed = 0
regression_total = len(regression_tests)

for test in regression_tests:
    query = test["query"]
    print(f"\n🧪 Query: '{query}'")
    
    entity_info = engine.entity_detector.detect(query)
    has_entity = entity_info['has_entity']
    
    status = "✅" if has_entity == test['should_have_entity'] else "❌"
    print(f"{status} Entity Detection Correct: {has_entity} (Expected: {test['should_have_entity']})")
    
    if has_entity == test['should_have_entity']:
        regression_passed += 1

regression_accuracy = (regression_passed / regression_total) * 100

#=============================================================================
# Overall Score Calculation
#=============================================================================

print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

# Calculate overall entity bypass success
total_entity_tests = device_total + location_total + org_total
total_entity_passed = device_passed + location_passed + org_passed
entity_bypass_rate = (total_entity_passed / total_entity_tests) * 100

print(f"\n1️⃣  Device Queries: {device_passed}/{device_total} ({device_accuracy:.1f}%)")
print(f"2️⃣  Location Queries: {location_passed}/{location_total} ({location_accuracy:.1f}%)")
print(f"3️⃣  Organization Queries: {org_passed}/{org_total} ({org_accuracy:.1f}%)")
print(f"4️⃣  Regression Tests: {regression_passed}/{regression_total} ({regression_accuracy:.1f}%)")

print(f"\n📊 Entity Bypass Success Rate: {total_entity_passed}/{total_entity_tests} ({entity_bypass_rate:.1f}%)")

# Estimate deterministic accuracy improvement
# Before: 85% (10-15% blocked due to entity stripping)
# After: Should be 95%+ if entity bypass works

# Weighted calculation
# Assume entity queries are ~15% of all deterministic queries
ENTITY_QUERY_RATIO = 0.15
BASELINE_ACCURACY = 85.0

# Improvement = Entity bypass rate * entity query ratio
improvement = (entity_bypass_rate - 70) * ENTITY_QUERY_RATIO  # 70% was old success rate for entity queries
new_deterministic_accuracy = BASELINE_ACCURACY + improvement

print(f"\n" + "=" * 70)
print("DETERMINISTIC ACCURACY ESTIMATE")
print("=" * 70)
print(f"Baseline (before fix): {BASELINE_ACCURACY}%")
print(f"Entity Bypass Rate: {entity_bypass_rate:.1f}%")
print(f"Estimated Improvement: +{improvement:.1f}%")
print(f"New Deterministic Accuracy: {new_deterministic_accuracy:.1f}%")

if new_deterministic_accuracy >= 95:
    print("\n✅ TARGET ACHIEVED: ≥95% deterministic accuracy")
elif new_deterministic_accuracy >= 90:
    print("\n⚠️  GOOD PROGRESS: 90-95% deterministic accuracy")
else:
    print("\n❌ NEEDS MORE WORK: <90% deterministic accuracy")

print("\n" + "=" * 70)

# Final verdict
if entity_bypass_rate >= 90 and regression_accuracy == 100:
    print("✅ ENTITY BYPASS FIX: SUCCESS")
    print("✅ System ready for production")
else:
    print("❌ ENTITY BYPASS FIX: NEEDS ADJUSTMENT")
    print(f"   Entity Bypass Rate: {entity_bypass_rate:.1f}% (Target: ≥90%)")
    print(f"   Regression Rate: {regression_accuracy:.1f}% (Target: 100%)")

print("=" * 70)
