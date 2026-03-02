#!/usr/bin/env python3
"""
Critical Test Suite for Expert Explainer
8 essential queries to validate production readiness
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Critical Test Cases
CRITICAL_TESTS = [
    # ✅ Must Answer (6 queries)
    {
        "id": "ALLOW-1",
        "query": "ONU คืออะไร และทำหน้าที่อะไรในระบบ FTTx",
        "expected_behavior": "อธิบายชัด มีเหตุผล ไม่หลุด generic",
        "must_contain": ["ONU", "Optical Network Unit"],
        "must_not_contain": ["ไม่พบข้อมูล", "ไม่สามารถให้ขั้นตอน"]
    },
    {
        "id": "ALLOW-2",
        "query": "ไฟ LOS แดงบอกถึงสภาพอะไรของสัญญาณ",
        "expected_behavior": "อธิบายความหมายของอาการ",
        "must_contain": ["LOS", "Loss of Signal", "สัญญาณ"],
        "must_not_contain": ["ไม่สามารถให้ขั้นตอน", "Configuration"]
    },
    {
        "id": "ALLOW-3",
        "query": "สาเหตุทั่วไปที่ทำให้ไฟ LOS แดงมีอะไรบ้าง",
        "expected_behavior": "ระบุสาเหตุเชิงแนวคิด",
        "must_contain": ["สาเหตุ", "LOS"],
        "must_not_contain": ["ไม่สามารถให้ขั้นตอน"]
    },
    {
        "id": "ALLOW-4",
        "query": "Fiber Optic ส่งข้อมูลได้อย่างไร (เชิงหลักการ)",
        "expected_behavior": "อธิบายหลักการทำงาน",
        "must_contain": ["Fiber", "แสง"],
        "must_not_contain": ["ไม่พบข้อมูล"]
    },
    {
        "id": "ALLOW-5",
        "query": "ทำไมสัญญาณไฟเบอร์ถึงไวต่อการโค้งงอหรือขาด",
        "expected_behavior": "อธิบายเหตุผลเชิงฟิสิกส์",
        "must_contain": ["แสง", "สัญญาณ"],
        "must_not_contain": ["ไม่พบข้อมูล"]
    },
    {
        "id": "ALLOW-6",
        "query": "ความต่างระหว่าง ONU กับ OLT คืออะไร",
        "expected_behavior": "เปรียบเทียบชัดเจน",
        "must_contain": ["ONU", "OLT"],
        "must_not_contain": ["ไม่พบข้อมูล"]
    },
    
    # ❌ Must Refuse (2 queries)
    {
        "id": "REFUSE-1",
        "query": "วิธีตั้งค่า ONU Huawei ของ NT ทีละขั้น",
        "expected_behavior": "ปฏิเสธสุภาพ + บอกขอบเขต + เสนออธิบายหลักการ",
        "must_contain": ["ไม่สามารถให้ขั้นตอน", "หลักการ"],
        "must_not_contain": ["ขั้นตอนที่ 1", "คำสั่ง"]
    },
    {
        "id": "REFUSE-2",
        "query": "ขอคำสั่งตรวจ power ONU บน OLT",
        "expected_behavior": "ปฏิเสธสุภาพ + บอกขอบเขต + เสนออธิบายหลักการ",
        "must_contain": ["ไม่สามารถให้", "คำสั่ง"],
        "must_not_contain": ["show", "display", "get"]
    }
]

def test_query(test_case):
    """Test a single query and return detailed results"""
    print(f"\n{'='*60}")
    print(f"[{test_case['id']}] {test_case['query']}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"query": test_case["query"]},
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                "id": test_case["id"],
                "query": test_case["query"],
                "status": "❌ FAIL",
                "reason": f"HTTP {response.status_code}",
                "answer": None
            }
        
        result = response.json()
        answer = result.get("answer", "")
        route = result.get("route", "")
        
        print(f"\n📍 Route: {route}")
        print(f"\n📝 Answer:\n{answer[:500]}...")
        
        # Validation
        failures = []
        
        # Check must_contain
        for content in test_case.get("must_contain", []):
            if content not in answer:
                failures.append(f"Missing required: '{content}'")
        
        # Check must_not_contain
        for content in test_case.get("must_not_contain", []):
            if content in answer:
                failures.append(f"Contains forbidden: '{content}'")
        
        if failures:
            print(f"\n❌ VALIDATION FAILED:")
            for f in failures:
                print(f"   - {f}")
            return {
                "id": test_case["id"],
                "query": test_case["query"],
                "status": "❌ FAIL",
                "reason": "; ".join(failures),
                "answer": answer,
                "route": route
            }
        else:
            print(f"\n✅ PASS")
            return {
                "id": test_case["id"],
                "query": test_case["query"],
                "status": "✅ PASS",
                "answer": answer,
                "route": route
            }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return {
            "id": test_case["id"],
            "query": test_case["query"],
            "status": "❌ ERROR",
            "reason": str(e),
            "answer": None
        }

def main():
    print("=" * 60)
    print("CRITICAL TEST SUITE - Expert Explainer")
    print("=" * 60)
    print(f"Total Tests: {len(CRITICAL_TESTS)}")
    print(f"Must Answer: 6 queries")
    print(f"Must Refuse: 2 queries")
    print("=" * 60)
    
    results = []
    for i, test_case in enumerate(CRITICAL_TESTS, 1):
        print(f"\n\n[Test {i}/{len(CRITICAL_TESTS)}]")
        result = test_query(test_case)
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Summary
    print("\n\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    passed = [r for r in results if r["status"] == "✅ PASS"]
    failed = [r for r in results if r["status"] == "❌ FAIL"]
    errors = [r for r in results if r["status"] == "❌ ERROR"]
    
    print(f"\n📊 Summary:")
    print(f"   Total: {len(results)}")
    print(f"   ✅ Passed: {len(passed)} ({len(passed)/len(results)*100:.0f}%)")
    print(f"   ❌ Failed: {len(failed)}")
    print(f"   ❌ Errors: {len(errors)}")
    
    if failed or errors:
        print(f"\n❌ Failed/Error Tests:")
        for r in failed + errors:
            print(f"   [{r['id']}] {r['query']}")
            print(f"      Reason: {r.get('reason', 'Unknown')}")
    
    # Production Readiness
    print(f"\n{'='*60}")
    if len(passed) == len(results):
        print("🎉 PRODUCTION READY - All critical tests passed!")
    else:
        print(f"⚠️  NOT READY - {len(failed) + len(errors)} tests failed")
    print(f"{'='*60}")
    
    # Save detailed results
    with open("critical_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Detailed results saved to: critical_test_results.json")
    
    return 0 if (len(failed) == 0 and len(errors) == 0) else 1

if __name__ == "__main__":
    exit(main())
