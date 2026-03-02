"""
Test Fast Path Skip Logic (Enhanced)

Tests that Fast Path is skipped for:
1. Menu/Collection pages (original request)
2. Concept/Knowledge pages (new request)
   - "ส่วนประกอบ คอมพิวเตร์" → Should SKIP → Summary
"""

print("=" * 70)
print("Fast Path Skip Logic Test")
print("=" * 70)

skip_patterns = [
    "ต่างๆ", "รวม", "เมนู", "ทั้งหมด", "หลายๆ", "index",
    "ส่วนประกอบ", "ความรู้", "พื้นฐาน", "คือ", "หลักการ", "การทำงาน", "overview", "introduction", "basic"
]

test_cases = [
    # Menu cases
    ("การติดตั้ง Modem 9ต่างๆ", True, "Has 'ต่างๆ'"),
    ("เมนูรวม Cisco", True, "Has 'เมนู'"),
    
    # Concept cases (New)
    ("ส่วนประกอบ คอมพิวเตร์", True, "Has 'ส่วนประกอบ' (Typos/Normal checked by contains)"),
    ("ความรู้ทั่วไป", True, "Has 'ความรู้'"),
    ("Network Basic", True, "Has 'Basic'"),
    ("หลักการทำงาน VLAN", True, "Has 'หลักการ'/'การทำงาน'"),
    
    # Normal cases (Fast Path OK)
    ("How to config Huawei", False, "How-to/Config → Use Fast Path"),
    ("FTTx Configuration Guide", False, "Config Guide → Use Fast Path"),
    ("Modem Spec V1", False, "Spec/Manual → Use Fast Path"),
]

print("\nTest Cases:")
print("-" * 70)

all_pass = True
for title, should_skip, reason in test_cases:
    title_lower = title.lower()
    should_skip_actual = any(p in title_lower for p in skip_patterns)
    
    status = "✅ " if should_skip_actual == should_skip else "❌"
    all_pass = all_pass and (should_skip_actual == should_skip)
    
    print(f"{status} '{title}'")
    print(f"   Expected: {'SKIP' if should_skip else 'USE'} Fast Path")
    print(f"   Got:      {'SKIP' if should_skip_actual else 'USE'} Fast Path")
    print(f"   Reason:   {reason}")
    print()

print("=" * 70)
if all_pass:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)
