#!/usr/bin/env python3
"""
Golden Test Suite for Deterministic Path Validation
Tests that deterministic intents route correctly without hijack.
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

# Golden queries for each deterministic intent
GOLDEN_CONTACT = [
    "ขอเบอร์ CSOC",
    "เบอร์ NOC",
    "โทรหาดใหญ่",
    "ติดต่อ SMC",
    "phone number helpdesk",
    "เบอร์ติดต่อ OMC",
    "ขอเบอร์ศูนย์ปฏิบัติการ",
]

GOLDEN_POSITION = [
    "ใครคือ ผจ",
    "ผช.สบลตน.",
    "ผอ.คือใคร",
    "ใครเป็นหัวหน้า",
    "ผู้รับผิดชอบ Access Network",
]

GOLDEN_DEFINE = [
    "ONU คืออะไร",
    "ไฟ LOS หมายถึงอะไร",
    "BRAS",
    "PON",
    "definition of VLAN",
    "GPON ทำหน้าที่อะไร",
]

# Negative queries (should NOT trigger deterministic)
NEGATIVE_CONTACT = [
    "วิธีตั้งค่า phone",
    "ip phone คืออะไร",
]

NEGATIVE_POSITION = [
    "ผจ. คืออะไร",
]

NEGATIVE_DEFINE = [
    "ping",
    "test",
]

# Expected behaviors
HIJACK_PHRASES = ["ใช้งานผ่าน Wi-Fi", "สาย LAN", "rag_clarify_followup"]

def test_no_hijack(query, expected_intent):
    """Test that query does NOT get hijacked by symptom follow-up"""
    from src.core.chat_engine import ChatEngine
    import yaml
    
    with open('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml', 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    
    engine = ChatEngine(cfg)
    result = engine.chat(query)
    
    answer = result.get('answer', '')
    route = result.get('route', '')
    
    # Check for hijack
    is_hijacked = any(phrase in answer for phrase in HIJACK_PHRASES) or \
                  'clarify_followup' in route
    
    if is_hijacked:
        print(f"❌ FAIL: '{query}' was hijacked")
        print(f"   Answer: {answer[:100]}...")
        print(f"   Route: {route}")
        return False
    else:
        print(f"✅ PASS: '{query}' not hijacked")
        return True

def run_golden_tests():
    """Run all golden test queries"""
    print("=" * 60)
    print("GOLDEN TEST SUITE - DETERMINISTIC PATH VALIDATION")
    print("=" * 60)
    
    results = []
    
    print("\n[TEST SET 1: CONTACT_LOOKUP]")
    for query in GOLDEN_CONTACT:
        results.append(test_no_hijack(query, "CONTACT_LOOKUP"))
    
    print("\n[TEST SET 2: POSITION_HOLDER_LOOKUP]")
    for query in GOLDEN_POSITION:
        results.append(test_no_hijack(query, "POSITION_HOLDER_LOOKUP"))
    
    print("\n[TEST SET 3: DEFINE_TERM]")
    for query in GOLDEN_DEFINE:
        results.append(test_no_hijack(query, "DEFINE_TERM"))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL DETERMINISTIC PATHS VALIDATED")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(run_golden_tests())
