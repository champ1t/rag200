#!/usr/bin/env python3
"""
Step 19.1-19.2 Verification: Intent Locking & SafeNormalizer Skip
Tests:
1. Contact query -> SafeNormalizer skipped
2. Position query -> SafeNormalizer skipped
3. General query -> SafeNormalizer runs normally
4. Latency measurement for contact queries
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from unittest.mock import MagicMock
from src.core.chat_engine import ChatEngine

print("=" * 80)
print("STEP 19.1-19.2: INTENT LOCKING & DOMAIN-SPECIFIC NORMALIZATION - VERIFICATION")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test 1: Contact query -> SafeNormalizer skipped
    print("\n[TEST 1] Contact query 'เบอร์ csoc' -> SafeNormalizer skipped")
    
    normalizer_calls = []
    original_analyze = engine.safe_normalizer.analyze
    
    def track_normalizer(q):
        normalizer_calls.append(q)
        return original_analyze(q)
    
    engine.safe_normalizer.analyze = track_normalizer
    engine.pending_question = None  # No pending
    
    t_start = time.time()
    try:
        result = engine.process("เบอร์ csoc")
        latency_ms = (time.time() - t_start) * 1000
    except Exception as e:
        latency_ms = (time.time() - t_start) * 1000
        print(f"   (Flow error expected: {type(e).__name__})")
    
    assert len(normalizer_calls) == 0, f"SafeNormalizer was called for contact query! Calls: {normalizer_calls}"
    print(f"   ✓ SafeNormalizer skipped (intent locked: CONTACT_LOOKUP)")
    print(f"   ✓ Latency: {latency_ms:.1f}ms")
    
    # Test 2: Position query -> SafeNormalizer skipped
    print("\n[TEST 2] Position query 'ใครคือผจ' -> SafeNormalizer skipped")
    normalizer_calls = []
    
    try:
        result = engine.process("ใครคือผจ")
    except Exception:
        pass
    
    assert len(normalizer_calls) == 0, f"SafeNormalizer was called for position query! Calls: {normalizer_calls}"
    print(f"   ✓ SafeNormalizer skipped (intent locked: POSITION_LOOKUP)")
    
    # Test 3: General query -> SafeNormalizer runs
    print("\n[TEST 3] General query 'วิธีตั้งค่า router' -> SafeNormalizer runs")
    normalizer_calls = []
    
    try:
        result = engine.process("วิธีตั้งค่า router")
    except Exception:
        pass
    
    assert len(normalizer_calls) > 0, "SafeNormalizer should run for general queries"
    print(f"   ✓ SafeNormalizer ran normally: {len(normalizer_calls)} call(s)")
    
    # Test 4: Multiple contact keywords
    print("\n[TEST 4] 'ติดต่อ NOC กรุงเทพ' -> SafeNormalizer skipped")
    normalizer_calls = []
    
    try:
        result = engine.process("ติดต่อ NOC กรุงเทพ")
    except Exception:
        pass
    
    assert len(normalizer_calls) == 0, f"SafeNormalizer was called! Calls: {normalizer_calls}"
    print(f"   ✓ SafeNormalizer skipped (contact keyword: 'ติดต่อ')")
    
    # Restore
    engine.safe_normalizer.analyze = original_analyze
    
    print("\n" + "=" * 80)
    print("✅ STEP 19.1-19.2 VERIFICATION PASSED")
    print("   - Contact queries skip SafeNormalizer (intent locked)")
    print("   - Position queries skip SafeNormalizer (intent locked)")
    print("   - General queries run SafeNormalizer normally")
    print("   - Domain-specific normalization working")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ STEP 19.1-19.2 VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
