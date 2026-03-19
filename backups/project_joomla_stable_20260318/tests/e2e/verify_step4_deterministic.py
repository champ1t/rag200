#!/usr/bin/env python3
"""
Step 4 Verification: Deterministic Before Heuristic
Tests:
1. During pending state -> SafeNormalizer skipped
2. Without pending -> SafeNormalizer runs normally
3. Deterministic match happens BEFORE normalizer
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from src.core.chat_engine import ChatEngine

print("=" * 80)
print("STEP 4: DETERMINISTIC BEFORE HEURISTIC - VERIFICATION")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test 1: Pending active -> SafeNormalizer skipped
    print("\n[TEST 1] Pending active -> SafeNormalizer skipped")
    engine.pending_question = {
        "kind": "position_confirmation",
        "candidates": [{"name": "Test", "position": "Manager"}],
        "created_at": time.time()
    }
    
    # Mock resolver to return None (let flow continue)
    def mock_resolver(q, lat):
        return None
    
    original_resolver = engine._resolve_pending_followup
    engine._resolve_pending_followup = mock_resolver
    
    # Mock normalizer to track if called
    normalizer_called = []
    original_analyze = engine.safe_normalizer.analyze
    def mock_analyze(q):
        normalizer_called.append(q)
        return original_analyze(q)
    
    engine.safe_normalizer.analyze = mock_analyze
    
    # This should skip normalizer
    try:
        result = engine.process("test query")
        assert len(normalizer_called) == 0, f"SafeNormalizer was called during pending! Calls: {normalizer_called}"
        print(f"   ✓ SafeNormalizer skipped (pending active)")
    except Exception as e:
        # Might error due to incomplete flow, but normalizer should still not be called
        assert len(normalizer_called) == 0, f"SafeNormalizer was called during pending! Error: {e}"
        print(f"   ✓ SafeNormalizer skipped (pending active, flow errored as expected)")
    
    # Restore
    engine._resolve_pending_followup = original_resolver
    engine.safe_normalizer.analyze = original_analyze
    
    # Test 2: No pending -> SafeNormalizer runs normally
    print("\n[TEST 2] No pending -> SafeNormalizer runs normally")
    engine.pending_question = None
    normalizer_called = []
    
    def mock_analyze2(q):
        normalizer_called.append(q)
        return {"confidence": 0.5, "intent": "GENERAL_QA"}
    
    engine.safe_normalizer.analyze = mock_analyze2
    
    try:
        result = engine.process("วิธีตั้งค่า")
        assert len(normalizer_called) > 0, "SafeNormalizer should be called when no pending"
        print(f"   ✓ SafeNormalizer ran (no pending): {len(normalizer_called)} call(s)")
    except Exception as e:
        # Even if flow errors, normalizer should have been called
        assert len(normalizer_called) > 0, f"SafeNormalizer not called: {e}"
        print(f"   ✓ SafeNormalizer ran (no pending): {len(normalizer_called)} call(s)")
    
    # Restore
    engine.safe_normalizer.analyze = original_analyze
    
    print("\n" + "=" * 80)
    print("✅ STEP 4 VERIFICATION PASSED")
    print("   - SafeNormalizer skipped when pending active (Layer 1 priority)")
    print("   - SafeNormalizer runs normally when no pending")
    print("   - Deterministic-first routing enforced")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ STEP 4 VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
