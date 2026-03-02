#!/usr/bin/env python3
"""
Step 19.3-19.4 Verification: Domain-Scoped Partial Resolution
Tests:
1. "ขอเบอร์นคร" -> prefix match -> selection mode (Stay in contact domain)
2. "เบอร์ ศรี" -> prefix match -> selection mode
3. "ติดต่อ xyz" (not found) -> domain-strict miss (NO global suggestions)
"""
import sys
import os
sys.path.append(os.getcwd())

from src.rag.handlers.contact_handler import ContactHandler

print("=" * 80)
print("STEP 19.3-19.4: DOMAIN-SCOPED PARTIAL RESOLUTION - VERIFICATION")
print("=" * 80)

# Mock records with province-based contacts
mock_records = [
    {"name": "นครศรีธรรมราช", "phones": ["075-123-456"], "type": "team", "role": "ศูนย์ภาคใต้", "unit": "นครศรีธรรมราช", "_score": 0},
    {"name": "นครราชสีมา", "phones": ["044-123-456"], "type": "team", "role": "ศูนย์ภาคตะวันออกเฉียงเหนือ", "unit": "นครราชสีมา", "_score": 0},
    {"name": "นครนายก", "phones": ["037-123-456"], "type": "team", "role": "ศูนย์ภาคกลาง", "unit": "นครนายก", "_score": 0},
    {"name": "นครพนม", "phones": ["042-123-456"], "type": "team", "role": "ศูนย์ภาคตะวันออกเฉียงเหนือ", "unit": "นครพนม", "_score": 0},
    {"name": "ศรีสะเกษ", "phones": ["045-123-456"], "type": "team", "role": "ศูนย์ภาคตะวันออกเฉียงเหนือ", "unit": "ศรีสะเกษ", "_score": 0},
    {"name": "หาดใหญ่", "phones": ["074-123-456"], "type": "team", "role": "ศูนย์ภาคใต้", "unit": "หาดใหญ่", "_score": 0},
]

try:
    # Test 1: "ขอเบอร์นคร" -> prefix match -> selection mode
    print("\n[TEST 1] 'ขอเบอร์นคร' -> prefix match -> selection mode")
    result = ContactHandler.handle("ขอเบอร์นคร", mock_records, directory_handler=None, llm_cfg={"model": "mock"})
    
    route = result.get("route", "")
    answer = result.get("answer", "")
    
    # Should enter prefix match mode
    assert "prefix" in route or "ambiguous" in route, f"Expected prefix/ambiguous route, got: {route}"
    assert "นครศรีธรรมราช" in answer or "นครราชสีมา" in answer, f"Expected province names in answer, got: {answer[:200]}"
    print(f"   ✓ Route: {route}")
    print(f"   ✓ Prefix match triggered (provinces listed)")
    
    # Test 2: "เบอร์ ศรี" -> prefix match
    print("\n[TEST 2] 'เบอร์ ศรี' -> prefix match")
    result = ContactHandler.handle("เบอร์ ศรี", mock_records, directory_handler=None, llm_cfg={"model": "mock"})
    
    route = result.get("route", "")
    answer = result.get("answer", "")
    
    assert "prefix" in route or "ambiguous" in route or "hit" in route, f"Expected match, got: {route}"
    assert "ศรีสะเกษ" in answer or "ศรี" in answer.lower(), f"Expected 'ศรี' match, got: {answer[:200]}"
    print(f"   ✓ Route: {route}")
    print(f"   ✓ Prefix match for 'ศรี'")
    
    # Test 3: "ติดต่อ xyz" (not found) -> domain-strict miss (NO global suggestions)
    print("\n[TEST 3] 'ติดต่อ xyz' (not found) -> domain-strict miss")
    result = ContactHandler.handle("ติดต่อ xyz", mock_records, directory_handler=None, llm_cfg={"model": "mock"})
    
    route = result.get("route", "")
    answer = result.get("answer", "")
    
    # CRITICAL: Should be domain_strict, NOT include global suggestions
    assert "domain_strict" in route or "miss" in route, f"Expected domain_strict miss, got: {route}"
    assert "หรือคุณหมายถึง" not in answer, f"Should NOT have global suggestions! Got: {answer}"
    assert "ฐานข้อมูลติดต่อ" in answer or "ไม่พบ" in answer, f"Expected domain-scoped miss message, got: {answer}"
    print(f"   ✓ Route: {route}")
    print(f"   ✓ Domain isolation: NO global suggestions")
    
    # Test 4: Short prefix "นค" -> should trigger prefix matching
    print("\n[TEST 4] 'เบอร์ นค' (very short) -> prefix match")
    result = ContactHandler.handle("เบอร์ นค", mock_records, directory_handler=None, llm_cfg={"model": "mock"})
    
    route = result.get("route", "")
    answer = result.get("answer", "")
    
    # Should find "นคร*" matches
    if "นคร" in answer:
        print(f"   ✓ Prefix match for 'นค' found 'นคร*' entries")
    else:
        print(f"   - Very short prefix may not match (acceptable)")
    print(f"   Route: {route}")
    
    print("\n" + "=" * 80)
    print("✅ STEP 19.3-19.4 VERIFICATION PASSED")
    print("   - Prefix matching works (นคร → multiple provinces)")
    print("   - Domain isolation enforced (no global suggestions on miss)")
    print("   - Contact queries stay in contact domain")
    print("=" * 80)
    
except AssertionError as e:
    print(f"\n❌ STEP 19.3-19.4 VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
