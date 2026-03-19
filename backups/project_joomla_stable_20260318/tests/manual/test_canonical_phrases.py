#!/usr/bin/env python3
"""
Test Canonical Phrase Rules
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.canonical_phrases import (
    get_canonical_phrase,
    boost_score_for_canonical,
    apply_canonical_rules
)

print("=== Canonical Phrase Test ===\n")

# Test 1: Canonical phrase detection
print("## Canonical Phrase Detection\n")
test_queries = [
    ("ขอดูตาราง ipphone", "ip-phone", "ipphone → ip-phone"),
    ("ip phone config", "ip-phone", "ip phone → ip-phone"),
    ("ไอพีโฟน ที่ไหน", "ip-phone", "Thai variant"),
    ("proxy sip server", "sip-proxy", "sip proxy → sip-proxy"),
    ("เบอร์ OMC", None, "No canonical phrase"),
]

for query, expected_canonical, description in test_queries:
    canonical, rewritten = get_canonical_phrase(query)
    status = "✓ PASS" if canonical == expected_canonical else "✗ FAIL"
    
    print(f"{status} | {query}")
    print(f"  Expected: {expected_canonical}")
    print(f"  Got: {canonical}")
    print(f"  Rewritten: {rewritten}")
    print(f"  Description: {description}")
    print()

# Test 2: Score boosting
print("\n## Score Boosting\n")
candidates = [
    {"text": "IP Phone Network Diagram", "score": 0.7},
    {"text": "IP Network Configuration", "score": 0.75},
    {"text": "SIP Proxy Settings", "score": 0.6},
]

print("Original candidates:")
for c in candidates:
    print(f"  {c['text']}: {c['score']}")

canonical = "ip-phone"
boosted = []
for c in candidates:
    boosted_score = boost_score_for_canonical(c['text'], canonical, c['score'])
    boosted.append({**c, 'boosted_score': boosted_score})

print(f"\nAfter boosting for '{canonical}':")
for c in sorted(boosted, key=lambda x: x['boosted_score'], reverse=True):
    boost_pct = ((c['boosted_score'] / c['score']) - 1) * 100 if c['score'] > 0 else 0
    print(f"  {c['text']}: {c['score']} → {c['boosted_score']:.2f} (+{boost_pct:.0f}%)")

# Test 3: Full pipeline
print("\n## Full Pipeline Test\n")
query = "ขอดูตาราง ipphone"
candidates = [
    {"text": "IP Phone Network Diagram", "score": 0.65},
    {"text": "IP Network Planning", "score": 0.70},
    {"text": "SIP Proxy Configuration", "score": 0.60},
]

print(f"Query: {query}")
print("Candidates before:")
for c in candidates:
    print(f"  {c['text']}: {c['score']}")

rewritten, boosted = apply_canonical_rules(query, candidates)

print(f"\nRewritten query: {rewritten}")
print("Candidates after boosting:")
for c in boosted:
    boost_marker = " ⭐" if c.get('boosted') else ""
    print(f"  {c['text']}: {c['score']:.2f}{boost_marker}")
