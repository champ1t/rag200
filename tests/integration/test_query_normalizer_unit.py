#!/usr/bin/env python3
"""
Unit Tests for Enhanced QueryNormalizer with Colloquial Patterns
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.query_normalizer import QueryNormalizer

# Mock LLM config
llm_cfg = {
    "fast_model": "llama3.2:3b",
    "base_url": "http://localhost:11434"
}

normalizer = QueryNormalizer(llm_cfg)

print("=" * 70)
print("QueryNormalizer Enhancement - Unit Tests")
print("=" * 70)

# Test cases
test_cases = [
    # Colloquial intent mapping
    ("อยากติดต่อ CSOC", "ขอเบอร์ CSOC", "Intent mapping: อยากติดต่อ → ขอเบอร์"),
    ("บอกเบอร์หาดใหญ่", "ขอเบอร์หาดใหญ่", "Intent mapping: บอกเบอร์ → ขอเบอร์"),
    ("อยากรู้เบอร์ OMC", "ขอเบอร์ OMC", "Intent mapping: อยากรู้เบอร์ → ขอเบอร์"),
    
    # Question normalization
    ("OLT ทำงานยังไง", "OLT ทำงานอย่างไร", "Question: ทำงานยังไง → ทำงานอย่างไร"),
    ("GPON ใช้ยังไง", "GPON ใช้อย่างไร", "Question: ใช้ยังไง → ใช้อย่างไร"),
    
    # Emphatic removal (backup)
    ("OLT มันคืออะไร", "OLT คืออะไร", "Emphatic: มันคืออะไร → คืออะไร"),
    
    # No change needed
    ("ขอเบอร์ OMC", "ขอเบอร์ OMC", "Already canonical - no change"),
    ("CSOC คืออะไร", "CSOC คืออะไร", "Already canonical - no change"),
]

passed = 0
total = len(test_cases)

for input_query, expected_output, description in test_cases:
    print(f"\n{'─'*70}")
    print(f"Test: {description}")
    print(f"Input: '{input_query}'")
    print(f"Expected: '{expected_output}'")
    
    # Apply patterns (not full normalize to avoid LLM)
    output, changed = normalizer._apply_colloquial_patterns(input_query)
    
    print(f"Output: '{output}'")
    print(f"Changed: {changed}")
    
    # Check result
    if output == expected_output:
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")
        print(f"   Expected: '{expected_output}'")
        print(f"   Got: '{output}'")

print(f"\n{'='*70}")
print(f"Results: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
print(f"{'='*70}")

# Test abbreviation preservation
print(f"\n{'='*70}")
print("Abbreviation Preservation Test")
print(f"{'='*70}")

abbrev_tests = [
    "OMC",
    "CSOC",
    "FTTx",
    "RNOC",
]

abbrev_passed = 0
for abbrev in abbrev_tests:
    test_query = f"อยากติดต่อ {abbrev}"
    output, _ = normalizer._apply_colloquial_patterns(test_query)
    
    if abbrev in output:
        print(f"✅ {abbrev} preserved in '{output}'")
        abbrev_passed += 1
    else:
        print(f"❌ {abbrev} NOT preserved in '{output}'")

print(f"\nAbbreviation Tests: {abbrev_passed}/{len(abbrev_tests)} passed")

# Overall result
print(f"\n{'='*70}")
overall_passed = passed + abbrev_passed
overall_total = total + len(abbrev_tests)
print(f"OVERALL: {overall_passed}/{overall_total} tests passed ({(overall_passed/overall_total)*100:.1f}%)")
print(f"{'='*70}")

if overall_passed == overall_total:
    print("\n🎉 All tests PASSED!")
    sys.exit(0)
else:
    print(f"\n⚠️ {overall_total - overall_passed} tests FAILED")
    sys.exit(1)
