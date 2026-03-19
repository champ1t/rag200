#!/usr/bin/env python3
"""
Test Contact Selection Pending State Fix - Direct Scenario
Simulates the exact bug: System enters contact_ambiguous, sets pending, user types "1"
"""
import sys
import os
import time
import json
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

print("=" * 80)
print("TEST: CONTACT SELECTION '1' INPUT BUG FIX")
print("=" * 80)

config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # SIMULATE: Manually set pending state (as if contact_ambiguous was returned)
    print("\n[SETUP] Simulating contact_ambiguous pending state")
    engine.pending_question = {
        "created_at": time.time(),
        "kind": "contact_choice",
        "candidates": [
            {"name": "นครศรีธรรมราช", "phones": ["075-123-456"], "role": "ศูนย์ภาคใต้"},
            {"name": "นครราชสีมา", "phones": ["044-123-456"], "role": "ศูนย์อีสาน"},
            {"name": "นครนายก", "phones": ["037-123-456"], "role": "ศูนย์กลาง"}
        ],
        "mode": "contact"
    }
    print(f"   ✅ Pending state set with {len(engine.pending_question['candidates'])} candidates")
    
    # BUG SCENARIO: User types "1"
    print("\n[TEST] User types '1' (should resolve contact #1)")
    result = engine.process("1")
    
    route = result.get("route", "")
    answer = result.get("answer", "")
    
    print(f"   Route: {route}")
    print(f"   Answer: {answer[:200]}...")
    
    # VERIFY FIX 1: Pre-Governance Gate intercepted
    if "contact_resolved_from_pending" in route:
        print(f"   ✅ FIX 1: Pre-Governance Gate intercepted '1'")
    else:
        print(f"   ❌ FAIL: Expected 'contact_resolved_from_pending', got: {route}")
        sys.exit(1)
    
    # VERIFY FIX 2: NOT routed to article (Governance override)
    if "article" in route or "blocked" in route:
        print(f"   ❌ FAIL: Governance overrode! Route: {route}")
        sys.exit(1)
    else:
        print(f"   ✅ FIX 2: Governance override blocked")
    
    # VERIFY FIX 4: Pending cleared
    if engine.pending_question is None:
        print(f"   ✅ FIX 4: Pending state cleared")
    else:
        print(f"   ❌ FAIL: Pending not cleared: {engine.pending_question}")
        sys.exit(1)
    
    # VERIFY: Correct contact resolved
    if "นครศรีธรรมราช" in answer:
        print(f"   ✅ Correct contact resolved (Choice #1)")
    else:
        print(f"   ❌ FAIL: Wrong contact! Answer: {answer}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ ALL FIXES VERIFIED!")
    print("   Bug: '1' during contact selection → Governance override to article ❌")
    print("   Fix: '1' during contact selection → Pre-Governance Gate → Resolve ✅")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
