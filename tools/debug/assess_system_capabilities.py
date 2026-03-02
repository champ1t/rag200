#!/usr/bin/env python3
"""
System Capability Assessment - Checkpoint 2026-02-13

Tests:
1. Deterministic Accuracy (100% for fixed answers)
2. Link Correctness (100% for all links)
3. LLM Query Interpretation (ChatGPT-like understanding)
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

import yaml
from pathlib import Path
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

print("=" * 70)
print("System Capability Assessment")
print("Baseline: checkpoint-2026-02-13-prefix-vendor-fixes")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

# =========================================================================
# Test Suite 1: Deterministic Accuracy (Fixed Answers)
# =========================================================================
print("\n" + "=" * 70)
print("Test 1: Deterministic Accuracy (Fixed Answers)")
print("=" * 70)

deterministic_tests = [
    {
        "query": "ขอเบอร์CSOC",
        "expected_contains": ["02-", "CSOC"],
        "category": "CONTACT"
    },
    {
        "query": "ขอเบอร์ศูนย์หาดใหญ่",
        "expected_contains": ["074-", "หาดใหญ่"],
        "category": "CONTACT"
    },
    {
        "query": "ผจ.สบลตน.",
        "expected_contains": ["ปรัชญา", "074-250685"],
        "category": "POSITION"
    },
    {
        "query": "VKL คืออะไร",
        "expected_contains": ["Virtual Knowledge", "SMC"],
        "category": "DEFINITION"
    }
]

det_passed = 0
det_total = len(deterministic_tests)

for test in deterministic_tests:
    query = test["query"]
    result = engine.query(query)
    answer = result.get('answer', '')
    route = result.get('route', '')
    
    # Check if all expected content is present
    all_found = all(exp in answer for exp in test['expected_contains'])
    
    status = "✅" if all_found else "❌"
    print(f"\n{status} Query: '{query}'")
    print(f"   Route: {route}")
    print(f"   Expected: {test['expected_contains']}")
    print(f"   Found: {all_found}")
    
    if all_found:
        det_passed += 1
    else:
        print(f"   Answer: {answer[:200]}")

det_accuracy = (det_passed / det_total) * 100
print(f"\n📊 Deterministic Accuracy: {det_passed}/{det_total} ({det_accuracy:.1f}%)")

# =========================================================================
# Test Suite 2: Link Correctness
# =========================================================================
print("\n" + "=" * 70)
print("Test 2: Link Correctness (100% Accuracy)")
print("=" * 70)

link_tests = [
    {
        "query": "ทะเบียนสินทรัพย์",
        "expected_link_contains": "article&id=568",
        "category": "ARTICLE"
    },
    {
        "query": "คู่มือ FTTx",
        "expected_link_contains": "view=article",
        "category": "ARTICLE"
    }
]

link_passed = 0
link_total = len(link_tests)

for test in link_tests:
    query = test["query"]
    result = engine.query(query)
    answer = result.get('answer', '')
    
    # Check if link is present and contains expected pattern
    has_link = "http://" in answer or "https://" in answer
    correct_link = test['expected_link_contains'] in answer if has_link else False
    
    status = "✅" if correct_link else "❌"
    print(f"\n{status} Query: '{query}'")
    print(f"   Has Link: {has_link}")
    print(f"   Correct Link: {correct_link}")
    
    if correct_link:
        link_passed += 1
    else:
        print(f"   Answer: {answer[:300]}")

link_accuracy = (link_passed / link_total) * 100
print(f"\n📊 Link Correctness: {link_passed}/{link_total} ({link_accuracy:.1f}%)")

# =========================================================================
# Test Suite 3: LLM Query Interpretation (ChatGPT-like)
# =========================================================================
print("\n" + "=" * 70)
print("Test 3: LLM Query Interpretation (Ambiguous/Colloquial)")
print("=" * 70)

interpretation_tests = [
    {
        "query": "ขอเบอร์ CSOC หน่อย",  # Colloquial + noise
        "expected_behavior": "Should understand 'ขอเบอร์' despite noise word 'หน่อย'",
        "should_succeed": True
    },
    {
        "query": "เบอร์โทรศัพท์ของ CSOC",  # Formal phrasing
        "expected_behavior": "Should normalize 'เบอร์โทรศัพท์' to phone lookup",
        "should_succeed": True
    },
    {
        "query": "อยากติดต่อหาดใหญ่",  # Indirect phrasing
        "expected_behavior": "Should interpret as contact request",
        "should_succeed": True
    },
    {
        "query": "OLT มันคืออะไรหว่า",  # Very colloquial
        "expected_behavior": "Should strip 'มัน', 'หว่า' and answer definition",
        "should_succeed": True
    }
]

interp_passed = 0
interp_total = len(interpretation_tests)

for test in interpretation_tests:
    query = test["query"]
    result = engine.query(query)
    answer = result.get('answer', '')
    route = result.get('route', '')
    
    # Check if answer is meaningful (not blocked/error)
    is_successful = (
        "ไม่พบข้อมูล" not in answer and
        "กรุณาระบุ" not in answer and
        "กว้างเกินไป" not in answer and
        len(answer) > 50  # Has substantial content
    )
    
    status = "✅" if is_successful else "❌"
    print(f"\n{status} Query: '{query}'")
    print(f"   Route: {route}")
    print(f"   Behavior: {test['expected_behavior']}")
    print(f"   Successful: {is_successful}")
    
    if is_successful:
        interp_passed += 1
    else:
        print(f"   Answer: {answer[:200]}")

interp_accuracy = (interp_passed / interp_total) * 100
print(f"\n📊 LLM Interpretation: {interp_passed}/{interp_total} ({interp_accuracy:.1f}%)")

# =========================================================================
# Overall Summary
# =========================================================================
print("\n" + "=" * 70)
print("OVERALL SYSTEM ASSESSMENT")
print("=" * 70)

print(f"\n1️⃣  Deterministic Accuracy: {det_accuracy:.1f}% ({det_passed}/{det_total})")
if det_accuracy >= 90:
    print("   ✅ EXCELLENT - Fixed answers are highly reliable")
elif det_accuracy >= 70:
    print("   ⚠️  GOOD - Minor improvements needed")
else:
    print("   ❌ NEEDS WORK - Significant deterministic failures")

print(f"\n2️⃣  Link Correctness: {link_accuracy:.1f}% ({link_passed}/{link_total})")
if link_accuracy == 100:
    print("   ✅ PERFECT - All links are correct")
elif link_accuracy >= 80:
    print("   ⚠️  GOOD - Some link issues")
else:
    print("   ❌ NEEDS WORK - Link accuracy problems")

print(f"\n3️⃣  LLM Interpretation: {interp_accuracy:.1f}% ({interp_passed}/{interp_total})")
if interp_accuracy >= 75:
    print("   ✅ GOOD - ChatGPT-like understanding")
elif interp_accuracy >= 50:
    print("   ⚠️  FAIR - Query normalization needs improvement")
else:
    print("   ❌ NEEDS WORK - Poor colloquial query handling")

overall = (det_accuracy + link_accuracy + interp_accuracy) / 3
print(f"\n📊 Overall Score: {overall:.1f}%")

if overall >= 85:
    print("✅ System is production-ready")
elif overall >= 70:
    print("⚠️  System is functional with room for improvement")
else:
    print("❌ System needs significant work")

print("\n" + "=" * 70)
