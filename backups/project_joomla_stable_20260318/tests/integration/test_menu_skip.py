"""
Test Smart Skip for Menu Pages

Simulates the exact scenarios:
1. "การติดตั้ง Modem 9ต่างๆ" → Should SKIP Fast Path → Go to content analysis
2. "How to config Huawei" → Should use Fast Path normally
"""

print("=" * 70)
print("Smart Skip Pattern Test")
print("=" * 70)

# Test patterns
menu_patterns = ["ต่างๆ", "รวม", "เมนู", "ทั้งหมด", "หลายๆ", "index"]

test_cases = [
    ("การติดตั้ง Modem 9ต่างๆ", True, "Has 'ต่างๆ' → Skip Fast Path"),
    ("เมนูรวม Cisco", True, "Has 'เมนู' and 'รวม' → Skip Fast Path"),
    ("Link ทั้งหมด", True, "Has 'ทั้งหมด' → Skip Fast Path"),
    ("How to config Huawei", False, "Normal title → Use Fast Path"),
    ("FTTx Configuration Guide", False, "Normal title → Use Fast Path"),
    ("Installation Steps", False, "Normal title → Use Fast Path"),
]

print("\nTest Cases:")
print("-" * 70)

all_pass = True
for title, should_skip, reason in test_cases:
    title_lower = title.lower()
    is_menu = any(p in title_lower for p in menu_patterns)
    
    status = "✅ " if is_menu == should_skip else "❌"
    all_pass = all_pass and (is_menu == should_skip)
    
    print(f"{status} '{title}'")
    print(f"   Expected: {'Skip' if should_skip else 'Use'} Fast Path")
    print(f"   Got:      {'Skip' if is_menu else 'Use'} Fast Path")
    print(f"   Reason:   {reason}")
    print()

print("=" * 70)
if all_pass:
    print("✅ ALL TESTS PASSED!")
    print("\nBehavior:")
    print("- Menu pages (ต่างๆ, รวม, etc.) → Skip Fast Path → Content analysis")
    print("- Normal pages → Fast Path as usual")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 70)
