#!/usr/bin/env python3
"""
Step 17.5-17.7: Test Routing Layer Priority Fix
Tests:
1. Confirmation tokens ("ใช่", "yes") during pending → resolve correctly (NOT greeting)
2. Pure greetings without pending → handled correctly
3. Expired pending + greeting → no crash
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from src.core.chat_engine import ChatEngine

print("=" * 80)
print("STEP 17.5-17.7: ROUTING LAYER PRIORITY FIX - VERIFICATION")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test 1: Confirmation token during pending resolves correctly (NOT greeting)
    print("\n[TEST 1] Confirmation token 'ใช่' during pending → resolved by Layer 1 (NOT greeting)")
    engine.pending_question = {
        "kind": "position_confirmation",
        "candidates": [{"name": "Test User", "position": "Manager"}],
        "created_at": time.time()
    }
    
    # Mock resolver to return success
    original_resolver = engine._resolve_pending_followup
    def mock_resolver(q, lat):
        if "ใช่" in q or "yes" in q.lower():
            return {
                "answer": "Confirmed selection",
                "route": "position_confirmed"
            }
        return None
    
    engine._resolve_pending_followup = mock_resolver
    
    result = engine.process("ใช่")
    print(f"   Route: {result.get('route')}")
    assert result.get('route') == 'position_confirmed', f"Expected position_confirmed, got {result.get('route')}"
    print("   ✓ 'ใช่' resolved by pending (Layer 1), NOT misclassified as greeting")
    
    # Restore original
    engine._resolve_pending_followup = original_resolver
    
    # Test 2: Pure greeting without pending → handled correctly by Layer 4
    print("\n[TEST 2] Pure greeting 'สวัสดี' without pending → Layer 4")
    engine.pending_question = None  # No pending
    
    result = engine.process("สวัสดี")
    print(f"   Route: {result.get('route')}")
    # Should hit greeting logic, not pending
    assert "greeting" in result.get('route', '').lower() or result.get('route') == 'greeting_gate', \
        f"Expected greeting route, got {result.get('route')}"
    print("   ✓ 'สวัสดี' handled by Layer 4 (greeting)")
    
    # Test 3: Expired pending + greeting token → no crash, handles gracefully
    print("\n[TEST 3] Expired pending + greeting 'สวัสดี' → no crash")
    engine.pending_question = {
        "kind": "article_selection",
        "candidates": [{"title": "Test", "url": "url1"}],
        "created_at": time.time() - 200  # Expired
    }
    
    result = engine.process("สวัสดี")
    print(f"   Route: {result.get('route')}")
    assert result.get('route') != 'system_error_fail_closed', \
        f"Got system_error_fail_closed on expired pending + greeting"
    print("   ✓ Expired pending + greeting handled gracefully (no crash)")
    
    # Test 4: Numeric input during pending NOT diverted to greeting
    print("\n[TEST 4] Numeric '1' during pending → resolved by Layer 1")
    engine.pending_question = {
        "kind": "article_selection",
        "candidates": [
            {"title": "Article 1", "url": "url1"},
            {"title": "Article 2", "url": "url2"}
        ],
        "created_at": time.time()
    }
    
    engine._handle_article_route = MagicMock(return_value={
        "answer": "Article response",
        "route": "article_direct"
    })
    
    result = engine.process("1")
    print(f"   Route: {result.get('route')}")
    assert result.get('route') == 'article_direct', f"Expected article_direct, got {result.get('route')}"
    print("   ✓ Numeric selection handled by pending (Layer 1)")
    
    print("\n" + "=" * 80)
    print("✅ STEP 17.5-17.7 VERIFICATION PASSED")
    print("   LAYER PRIORITY CORRECT:")
    print("   - Layer 1: Pending Resolver (handles 'ใช่', '1', confirmations)")
    print("   - Layer 4: Greeting (handles 'สวัสดี' ONLY when no pending)")
    print("   - No priority inversion")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ STEP 17.5-17.7 VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
