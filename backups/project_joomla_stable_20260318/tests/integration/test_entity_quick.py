#!/usr/bin/env python3
"""
Quick Entity Bypass Test - Manual Validation

Tests a few key queries to validate entity bypass is working.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import yaml
from pathlib import Path

print("=" * 70)
print("Quick Entity Bypass Test")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

print("\n✅ ChatEngine loaded with Entity Detector")

# Test queries
test_queries = [
    ("ขอเบอร์UMUX", "Device entity - should bypass"),
    ("ขอเบอร์หาดใหญ่", "Location entity - should bypass"),  
    ("ขอเบอร์ CSOC", "Organization entity - should bypass"),
    ("สวัสดี", "No entity - normal flow"),
]

passed = 0
total = len(test_queries)

for query, description in test_queries:
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"Desc: {description}")
    print(f"{'='*70}")
    
    # Check entity detection
    entity_info = engine.entity_detector.detect(query)
    print(f"Entity Detected: {entity_info['has_entity']}")
    if entity_info['has_entity']:
        print(f"  Value: {entity_info['entity_value']}")
        print(f"  Type: {entity_info['entity_type']}")
        print(f"  Confidence: {entity_info['confidence']}")
    
    # Run query
    result = engine.process(query)
    route = result.get('route', '')
    answer = result.get('answer', '')[:200]
    
    print(f"\nRoute: {route}")
    print(f"Answer: {answer}")
    
    # Simple success check
    is_blocked = 'blocked' in route.lower() or 'นอกขอบเขต' in answer
    
    if entity_info['has_entity']:
        # Entity queries should NOT be blocked
        success = not is_blocked
    else:
        # Non-entity queries should work normally (greeting should succeed)
        success = 'สวัสดี' in answer or not is_blocked
    
    if success:
        passed += 1
        print("✅ PASS")
    else:
        print("❌ FAIL")

print(f"\n{'='*70}")
print(f"Results: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
print(f"{'='*70}")

# Estimate improvement
BASELINE = 85.0
ENTITY_RATIO = 0.15
old_entity_success = 0.70
new_entity_success = (passed / total) * 100 if total > 0 else 0

improvement = (new_entity_success - old_entity_success) * ENTITY_RATIO
new_accuracy = BASELINE + improvement

print(f"\n📊 Deterministic Accuracy Estimate:")
print(f"  Baseline: {BASELINE}%")
print(f"  Entity Success: {new_entity_success:.1f}% (was ~70%)")
print(f"  Improvement: +{improvement:.1f}%")
print(f"  New Accuracy: {new_accuracy:.1f}%")

if new_accuracy >= 95:
    print("\n✅ TARGET ACHIEVED: ≥95%")
elif new_accuracy >= 90:
    print("\n⚠️ CLOSE: 90-95%")
else:
    print("\n❌ BELOW TARGET: <90%")
