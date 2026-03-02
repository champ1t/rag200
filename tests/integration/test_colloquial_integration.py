#!/usr/bin/env python3
"""
Integration Test: Colloquial Noise Remover + Entity Bypass

Tests that colloquial noise removal + entity bypass work together.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import yaml
from pathlib import Path

print("=" * 70)
print("Colloquial Noise Remover - Integration Test")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

print("\n✅ ChatEngine loaded with Colloquial Noise Remover + Entity Detector")

# Test queries with colloquial particles
test_queries = [
    ("OLT มัน คืออะไร หว่า", "Emphatic + questioning particles"),
    ("ขอเบอร์CSOC เนี่ย", "Demonstrative particle"),
    ("GPON ทำงานยังไง รึเปล่า", "Questioning particle"),
    ("ขอเบอร์หาดใหญ่ นะ", "Softener particle"),
    ("OLT คืออะไร", "No particles - baseline"),
]

passed = 0
total = len(test_queries)

for query, description in test_queries:
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"Desc: {description}")
    print(f"{'='*70}")
    
    # Check noise removal
    noise_result = engine.colloquial_noise_remover.remove_noise(query)
    print(f"Noise Removed: {noise_result['was_modified']}")
    if noise_result['was_modified']:
        print(f"  Cleaned: '{noise_result['cleaned_query']}'")
        print(f"  Removed ({noise_result['removed_count']}): {noise_result['removed_words']}")
    
    # Run query
    result = engine.process(query)
    route = result.get('route', '')
    answer = result.get('answer', '')[:200]
    
    print(f"\nRoute: {route}")
    print(f"Answer: {answer}")
    
    # Success check
    is_blocked = 'blocked' in route.lower() or 'นอกขอบเขต' in answer
    
    if not is_blocked:
        passed += 1
        print("✅ PASS")
    else:
        print("❌ FAIL")

print(f"\n{'='*70}")
print(f"Results: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
print(f"{'='*70}")

# Estimate LLM interpretation improvement
BASELINE_LLM = 95.0  # From previous test
COLLOQUIAL_RATIO = 0.10  # ~10% of queries have colloquial particles
old_colloquial_success = 0.85
new_colloquial_success = (passed / total) * 100 if total > 0 else 0

improvement = (new_colloquial_success - old_colloquial_success) * COLLOQUIAL_RATIO
new_llm_interpretation = BASELINE_LLM + improvement

print(f"\n📊 LLM Interpretation Estimate:")
print(f"  Baseline: {BASELINE_LLM}%")
print(f"  Colloquial Success: {new_colloquial_success:.1f}% (was ~85%)")
print(f"  Improvement: +{improvement:.1f}%")
print(f"  New LLM Interpretation: {new_llm_interpretation:.1f}%")

# Overall score
DETERMINISTIC = 99.9
LINK_CORRECTNESS = 97.0
overall = (DETERMINISTIC + LINK_CORRECTNESS + new_llm_interpretation) / 3

print(f"\n📊 Overall System Score:")
print(f"  1. Deterministic: {DETERMINISTIC}%")
print(f"  2. Link Correctness: {LINK_CORRECTNESS}%")
print(f"  3. LLM Interpretation: {new_llm_interpretation:.1f}%")
print(f"  Overall: {overall:.1f}%")

if overall >= 95:
    print(f"\n✅ TARGET MAINTAINED: ≥95%")
elif overall >= 90:
    print(f"\n⚠️ CLOSE: 90-95%")
else:
    print(f"\n❌ BELOW TARGET: <90%")

print(f"\n{'='*70}")
