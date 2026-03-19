#!/usr/bin/env python3
"""
Simplified Deterministic Validation Test
Tests critical deterministic routing scenarios
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.core.chat_engine import ChatEngine
import yaml

# Load config
with open('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

# Forbidden phrases that indicate hijack
FORBIDDEN = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]

def test_query(test_id, query, description):
    """Test a single query"""
    print(f"\n{'='*60}")
    print(f"[{test_id}] {description}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    try:
        engine = ChatEngine(cfg)
        result = engine.process(query)
        
        answer = result.get('answer', '')
        route = result.get('route', '')
        
        # Check for violations
        violations = [phrase for phrase in FORBIDDEN if phrase in answer or phrase in route]
        
        passed = len(violations) == 0
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"Status: {status}")
        print(f"Route: {route}")
        print(f"Answer: {answer[:150]}...")
        
        if violations:
            print(f"⚠️  VIOLATIONS: {', '.join(violations)}")
        
        return passed
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_context_isolation(test_id, queries, description):
    """Test multi-turn context isolation"""
    print(f"\n{'='*60}")
    print(f"[{test_id}] {description}")
    print(f"Queries: {queries}")
    print(f"{'='*60}")
    
    try:
        engine = ChatEngine(cfg)
        
        for i, q in enumerate(queries):
            print(f"\nTurn {i+1}: {q}")
            result = engine.process(q)
            
            if i == len(queries) - 1:
                # Test final query
                answer = result.get('answer', '')
                route = result.get('route', '')
                
                violations = [phrase for phrase in FORBIDDEN if phrase in answer or phrase in route]
                passed = len(violations) == 0
                status = "✅ PASS" if passed else "❌ FAIL"
                
                print(f"Status: {status}")
                print(f"Route: {route}")
                print(f"Answer: {answer[:150]}...")
                
                if violations:
                    print(f"⚠️  VIOLATIONS: {', '.join(violations)}")
                
                return passed
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 DETERMINISTIC LAYER VALIDATION - SIMPLIFIED")
    print("="*60)
    
    results = []
    
    # TEST SUITE A: DEFINE / EXPLAIN IMMUNITY
    print("\n\n📋 TEST SUITE A: DEFINE / EXPLAIN IMMUNITY")
    results.append(test_query("A1", "ONU คืออะไร", "Definition query must not trigger symptom follow-up"))
    results.append(test_query("A2", "ไฟ LOS คืออะไร", "Definition query must not trigger HOWTO or follow-up"))
    results.append(test_query("A3", "สรุปปัญหาไฟแดง ONU", "Summary query must answer directly without Wi-Fi/LAN question"))
    
    # TEST SUITE B: CONTACT_LOOKUP ISOLATION
    print("\n\n📋 TEST SUITE B: CONTACT_LOOKUP ISOLATION")
    results.append(test_query("B1", "ขอเบอร์ CSOC", "Contact lookup must not trigger follow-up"))
    results.append(test_context_isolation("B2", ["ONU ไฟแดง เน็ตใช้ไม่ได้", "ขอเบอร์ CSOC"], 
                                         "Contact lookup must ignore previous symptom context"))
    
    # TEST SUITE C: POSITION LOOKUP SAFETY
    print("\n\n📋 TEST SUITE C: POSITION LOOKUP SAFETY")
    results.append(test_query("C1", "ใครคือ ผจ", "Position lookup must not trigger symptom follow-up"))
    results.append(test_context_isolation("C2", ["ใครคือ ผจ", "ขอเบอร์ OMC"],
                                         "Contact lookup must not reference previous position query"))
    
    # FINAL VERDICT
    print("\n\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    total = len(results)
    passed = sum(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ DETERMINISTIC LOCKED")
        print("All tests passed. Deterministic layer is production-ready.")
        sys.exit(0)
    else:
        print(f"\n❌ NOT READY")
        print(f"Reason: {total - passed} test(s) failed")
        print("System requires fixes before production deployment.")
        sys.exit(1)
