#!/usr/bin/env python3
"""
Test script for QueryNormalizer Phase 2.1
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.query_normalizer import QueryNormalizer

# Test configuration
llm_cfg = {
    "fast_model": "llama3.2:3b",
    "base_url": "http://localhost:11434"
}

normalizer = QueryNormalizer(llm_cfg)

# Test cases
test_queries = [
    "เบอ OMC หาดใหญ่",           # Should normalize "เบอ" → "เบอร์"
    "ติดต่อ help desk",          # Should normalize "help desk" → "HelpDesk"
    "สมาชิก fttx",               # Should normalize "fttx" → "FTTx"
    "OMC",                        # Should stay unchanged (already canonical)
    "ตาราง proxy iphone",        # Real case from user's error
]

print("=== QueryNormalizer Test ===\n")

for query in test_queries:
    print(f"Input: '{query}'")
    result = normalizer.normalize(query, trigger_reason="test")
    print(f"  Normalized: '{result['normalized_query']}'")
    print(f"  Changed: {result['changed']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Latency: {result['latency_ms']:.1f}ms")
    print()
