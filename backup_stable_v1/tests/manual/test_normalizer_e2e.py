#!/usr/bin/env python3
"""
End-to-end test for QueryNormalizer Phase 2.1
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.chat_engine import ChatEngine

# Initialize ChatEngine
print("=== Initializing ChatEngine ===")
engine = ChatEngine()

# Test queries that should trigger normalization
test_cases = [
    {
        "query": "เบอ OMC หาดใหญ่",
        "expected": "Should normalize 'เบอ' → 'เบอร์' and retry lookup"
    },
    {
        "query": "ติดต่อ help desk",
        "expected": "Should normalize 'help desk' → 'HelpDesk' and retry"
    },
    {
        "query": "สมาชิก fttx",
        "expected": "Should normalize 'fttx' → 'FTTx' and retry"
    }
]

print("\n=== Testing QueryNormalizer Integration ===\n")

for i, test in enumerate(test_cases, 1):
    print(f"Test {i}: {test['query']}")
    print(f"Expected: {test['expected']}")
    
    try:
        response = engine.chat(test['query'])
        print(f"Response: {response.get('answer', 'N/A')[:200]}")
        print(f"Route: {response.get('route', 'N/A')}")
        print()
    except Exception as e:
        print(f"Error: {e}\n")
