#!/usr/bin/env python3
"""
Verification Script: Conversation State Hijack Fix
Tests that deterministic intents properly invalidate stale follow-up states.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.core.chat_engine import ChatEngine
import yaml

# Load config
with open('/Users/jakkapatmac/Documents/NT/RAG/rag_web/config.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

def test_hijack_prevention():
    """Test Case 1: Definition query should NOT be hijacked by pending contact choice"""
    print("=" * 60)
    print("TEST 1: Hijack Prevention (Primary Fix)")
    print("=" * 60)
    
    engine = ChatEngine(cfg)
    
    # Step 1: Trigger contact choice state
    print("\n[User] ขอเบอร์ CSOC")
    result1 = engine.chat("ขอเบอร์ CSOC")
    print(f"[System] {result1['answer'][:100]}...")
    print(f"[Route] {result1.get('route', 'N/A')}")
    
    # Verify pending state was created
    if engine.pending_question:
        print(f"✓ Pending state created: {engine.pending_question.get('kind', 'unknown')}")
    else:
        print("✗ FAIL: No pending state created")
        return False
    
    # Step 2: Ask definition question (should clear pending state)
    print("\n[User] ONU คืออะไร")
    result2 = engine.chat("ONU คืออะไร")
    print(f"[System] {result2['answer'][:150]}...")
    print(f"[Route] {result2.get('route', 'N/A')}")
    
    # Verify hijack was prevented
    if "เลือก" in result2['answer'] or "choice" in result2.get('route', ''):
        print("✗ FAIL: Query was hijacked by contact choice")
        return False
    elif "ONU" in result2['answer'] or "Optical" in result2['answer']:
        print("✓ PASS: Definition query processed correctly")
        return True
    else:
        print("? UNCERTAIN: Response unclear")
        return False

def test_legitimate_followup():
    """Test Case 2: Legitimate number selection should still work"""
    print("\n" + "=" * 60)
    print("TEST 2: Legitimate Follow-up Preserved")
    print("=" * 60)
    
    engine = ChatEngine(cfg)
    
    # Step 1: Trigger contact choice
    print("\n[User] ขอเบอร์ CSOC")
    result1 = engine.chat("ขอเบอร์ CSOC")
    print(f"[System] {result1['answer'][:100]}...")
    
    # Step 2: Select option 1
    print("\n[User] 1")
    result2 = engine.chat("1")
    print(f"[System] {result2['answer'][:150]}...")
    print(f"[Route] {result2.get('route', 'N/A')}")
    
    # Verify selection worked
    if "02-" in result2['answer'] or "phone" in result2.get('route', '').lower():
        print("✓ PASS: Legitimate selection processed correctly")
        return True
    else:
        print("✗ FAIL: Selection was not processed")
        return False

def test_position_lookup_not_hijacked():
    """Test Case 3: Position lookup should clear pending state"""
    print("\n" + "=" * 60)
    print("TEST 3: Position Lookup Not Hijacked")
    print("=" * 60)
    
    engine = ChatEngine(cfg)
    
    # Step 1: Trigger contact choice
    print("\n[User] ขอเบอร์ CSOC")
    result1 = engine.chat("ขอเบอร์ CSOC")
    print(f"[System] {result1['answer'][:100]}...")
    
    # Step 2: Ask position question
    print("\n[User] ใครคือ ผจ.สบลตน.")
    result2 = engine.chat("ใครคือ ผจ.สบลตน.")
    print(f"[System] {result2['answer'][:150]}...")
    print(f"[Route] {result2.get('route', 'N/A')}")
    
    # Verify hijack was prevented
    if "เลือก" in result2['answer']:
        print("✗ FAIL: Query was hijacked by contact choice")
        return False
    else:
        print("✓ PASS: Position lookup processed correctly")
        return True

if __name__ == "__main__":
    print("\n🔍 CONVERSATION STATE HIJACK FIX VERIFICATION\n")
    
    results = []
    results.append(("Hijack Prevention", test_hijack_prevention()))
    results.append(("Legitimate Follow-up", test_legitimate_followup()))
    results.append(("Position Lookup", test_position_lookup_not_hijacked()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(results, key=lambda x: x[1])
    print(f"\nTotal: {passed}/{total} tests passed")
    
    sys.exit(0 if passed == total else 1)
