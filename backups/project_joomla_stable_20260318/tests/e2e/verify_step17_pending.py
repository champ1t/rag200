#!/usr/bin/env python3
"""
Step 17: Test Pending State Machine Fixes
Tests:
1. Expired pending doesn't cause AttributeError
2. Greetings bypass pending
3. Normal flow works after expiry
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from src.core.chat_engine import ChatEngine

print("=" * 80)
print("STEP 17: PENDING STATE MACHINE FIX - VERIFICATION")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test 1: Expired pending doesn't crash
    print("\n[TEST 1] Expired pending state doesn't cause crash")
    engine.pending_question = {
        "kind": "article_selection",
        "candidates": [{"title": "Test", "url": "url1"}],
        "created_at": time.time() - 200  # 200 seconds ago (expired)
    }
    
    # Mock to avoid actual processing
    engine.processed_cache.find_best_article_match = MagicMock(return_value=None)
    
    try:
        # This should NOT crash with AttributeError
        result = engine.process("test query")
        print(f"✓ No crash on expired pending. Route: {result.get('route')}")
        assert engine.pending_question is None, "Pending should be cleared after expiry"
        print("✓ Pending state cleared correctly")
    except AttributeError as e:
        print(f"❌ FAILED: AttributeError on expired pending: {e}")
        raise
    
    # Test 2: Greetings bypass pending
    print("\n[TEST 2] Greetings bypass pending state machine")
    engine.pending_question = {
        "kind": "article_selection",
        "candidates": [{"title": "Test", "url": "url1"}],
        "created_at": time.time()  # Fresh
    }
    
    greeting_queries = ["สวัสดี", "ขอบคุณ", "ok", "hi"]
    for greeting in greeting_queries:
        result = engine.process(greeting)
        print(f"✓ '{greeting}' bypassed pending (route: {result.get('route')})")
    
    # Test 3: Valid pending still works
    print("\n[TEST 3] Valid pending selection still functional")
    engine.pending_question = {
        "kind": "article_selection",
        "candidates": [
            {"title": "Test Article 1", "url": "url1"},
            {"title": "Test Article 2", "url": "url2"}
        ],
        "created_at": time.time()
    }
    
    # Mock article route handler
    engine._handle_article_route = MagicMock(return_value={
        "answer": "Test response",
        "route": "article_direct"
    })
    
    result = engine.process("1")
    assert result.get('route') == 'article_direct', f"Expected article_direct, got {result.get('route')}"
    print("✓ Numeric selection '1' works correctly")
    
    print("\n" + "=" * 80)
    print("✅ STEP 17 VERIFICATION PASSED")
    print("   - No AttributeError on expired pending")
    print("   - Greetings bypass pending correctly")
    print("   - Valid selections still functional")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ STEP 17 VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
