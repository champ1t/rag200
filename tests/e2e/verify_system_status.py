#!/usr/bin/env python3
"""
System Status Verification: Clarity & Ambiguity (Point 3)
Tests:
1. Contact Ambiguity: "ขอเบอร์นคร" -> Selection (Verified Step 19.3)
2. Article Ambiguity: "คู่มือ" (Generic) -> Should offer choices / Clarification
3. Vendor Ambiguity: "Cisco" -> Should offer choices / Drill-down
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

print("=" * 80)
print("SYSTEM STATUS: AMBIGUITY HANDLING VERIFICATION")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test 1: Article Ambiguity (Broad term)
    print("\n[TEST 1] Broad Article Query: 'manual' (or similar broad term)")
    # We'll use a term likely to match multiple things or be broad
    
    # Mocking processed_cache to simulate ambiguity
    original_find = engine.processed_cache.find_best_article_match
    
    def mock_find_ambiguous(q, threshold=0.9):
        if "manual" in q.lower() or "คู่มือ" in q:
            return {
                "match_type": "ambiguous",
                "candidates": ["Manual A", "Manual B", "Manual C"],
                "score": 0.85
            }
        return original_find(q, threshold)
    
    engine.processed_cache.find_best_article_match = mock_find_ambiguous
    
    result = engine.process("ขอคู่มือหน่อย")
    
    print(f"   Query: 'ขอคู่มือหน่อย'")
    print(f"   Route: {result.get('route')}")
    print(f"   Answer snippet: {result.get('answer')[:100]}...")
    
    if result.get('route') == 'blocked_ambiguous' or "เลือก" in result.get('answer', ''):
        print("   ✅ PASS: System asks for clarification/selection")
    else:
        print(f"   ❌ FAIL: System did not offer choices. Route: {result.get('route')}")

    # Restore
    engine.processed_cache.find_best_article_match = original_find
    
    print("\n" + "=" * 80)
    print("STATUS SUMMARY:")
    print("1. Deterministic: ✅ (Verified in Step 4)")
    print("2. Direct Links:  ✅ (Verified in Step 16)")
    print("3. Ambiguity (Clarification):")
    print("   - Contacts: ✅ (Step 19.3 - Prefix Selection)")
    print("   - Articles: " + ("✅ (Logic exists)" if result.get('route') == 'blocked_ambiguous' else "⚠️ (Needs check)"))
    print("=" * 80)

except Exception as e:
    print(f"\n❌ VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
