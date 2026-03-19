import sys
sys.path.append('.')

# Test fast-path detection with actual NT-1 content
from src.rag.article_cleaner import has_structured_content, extract_structured_facts, clean_article_content

# Simulate NT-1 article content (simplified)
test_content = """ข่าว NT1
เขียนโดย Meru^
วันพฤหัสบดีที่ 08 พฤษภาคม 2025 เวลา 12:55 น.

1. URL ดู session ip  Broadband NT1 ใช้งานผ่าน IE เท่านั้น 61.19.143.4/office2 user: south pass: wdyrcd
2. หมายเลขติดต่อ RNOC (ลภก.3) 0-81417-0144
3. หาก ลูกค้าใช้กล่อง Cnema แล้วพบอาการ หมุน รับชมไม่ลื่นไหล ให้แจ้งเพื่อตรวจสอบที่ NOC Cnema เลขหมาย 08-1350-9735
4. Wireless Router ของ NT1 ครับ User : admin@tec Pass : admin +MAC 4 ตัวท้าย
5. ระบบ CSS (NT1) http://122.155.137.209:8080/sysworkflow/en/neoclassic/login/login User : 00913168 Pass : 12345
"""

print("Testing fast-path detection:")
print("="*60)

# Test 1: has_structured_content
print("\n1. Testing has_structured_content():")
has_structure = has_structured_content(test_content)
print(f"   Result: {has_structure}")
print(f"   Expected: True")

# Test 2: extract_structured_facts
print("\n2. Testing extract_structured_facts():")
facts = extract_structured_facts(test_content)
print(f"   Found {len(facts)} facts:")
for i, fact in enumerate(facts, 1):
    print(f"   {i}. {fact[:80]}...")

# Test 3: Clean content first
print("\n3. Testing with cleaned content:")
cleaned = clean_article_content(test_content, keep_metadata=True)
print(f"   Cleaned length: {len(cleaned)} chars")
has_structure_cleaned = has_structured_content(cleaned)
print(f"   has_structured_content: {has_structure_cleaned}")
facts_cleaned = extract_structured_facts(cleaned)
print(f"   Found {len(facts_cleaned)} facts")

print("\n" + "="*60)
print("Summary:")
print(f"- Original content: {len(facts)} facts, structured={has_structure}")
print(f"- Cleaned content: {len(facts_cleaned)} facts, structured={has_structure_cleaned}")
