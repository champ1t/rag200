#!/usr/bin/env python3
"""
Test Script for Expert Explainer Routing Logic Refinements
Tests META questions, DEFINE_TERM fallback, and Troubleshooting exemption
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test Cases
TEST_CASES = [
    # META Questions (Should return policy explanation)
    {
        "name": "META-1: System Decision Logic",
        "query": "คุณตัดสินใจอย่างไรว่าจะตอบหรือปฏิเสธ",
        "expected_route": "meta_explanation",
        "expected_content": ["อนุญาตให้ตอบ", "ปฏิเสธ", "การตัดสินใจ"]
    },
    {
        "name": "META-2: System Criteria",
        "query": "ระบบใช้เกณฑ์อะไรในการตอบคำถาม",
        "expected_route": "meta_explanation",
        "expected_content": ["อนุญาตให้ตอบ", "ปฏิเสธ"]
    },
    
    # DEFINE_TERM (Should use model knowledge even without RAG)
    {
        "name": "DEFINE-1: ONU Definition",
        "query": "ONU คืออะไร",
        "expected_route": "rag",
        "expected_content": ["ONU", "Optical Network Unit"],
        "should_not_contain": ["ไม่พบข้อมูล"]
    },
    {
        "name": "DEFINE-2: LOS Definition",
        "query": "LOS คืออะไร",
        "expected_route": "rag",
        "expected_content": ["LOS", "Loss of Signal"],
        "should_not_contain": ["ไม่พบข้อมูล"]
    },
    {
        "name": "DEFINE-3: GPON Definition",
        "query": "GPON คืออะไร",
        "expected_route": "rag",
        "expected_content": ["GPON", "Gigabit"],
        "should_not_contain": ["ไม่พบข้อมูล"]
    },
    
    # Troubleshooting (Should explain, not refuse)
    {
        "name": "TROUBLE-1: LOS Red Light",
        "query": "ไฟ LOS แดงคืออะไร",
        "expected_route": "rag",
        "expected_content": ["LOS", "Loss of Signal", "สัญญาณ"],
        "should_not_contain": ["ไม่สามารถให้ขั้นตอน", "Configuration"]
    },
    {
        "name": "TROUBLE-2: Alarm Blinking",
        "query": "ไฟ Alarm กระพริบหมายถึงอะไร",
        "expected_route": "rag",
        "expected_content": ["Alarm", "สัญญาณ"],
        "should_not_contain": ["ไม่สามารถให้ขั้นตอน"]
    },
    
    # Regression Tests (Should still refuse)
    {
        "name": "REGRESS-1: Config Request",
        "query": "config ONU ยังไง",
        "expected_route": "expert_refusal_fast",
        "expected_content": ["ไม่สามารถให้ขั้นตอน", "Configuration"]
    },
    {
        "name": "REGRESS-2: CLI Command",
        "query": "ขอคำสั่ง CLI เช็ค ONU",
        "expected_route": "expert_refusal_fast",
        "expected_content": ["ไม่สามารถให้ขั้นตอน"]
    },
    {
        "name": "REGRESS-3: Nonsense",
        "query": "วิธีชงกาแฟด้วย ONU",
        "expected_route": "expert_refusal_fast",
        "expected_content": ["ไม่เกี่ยวกับ"]
    }
]

def test_query(test_case):
    """Test a single query"""
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"query": test_case["query"]},
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                "name": test_case["name"],
                "status": "FAIL",
                "reason": f"HTTP {response.status_code}"
            }
        
        result = response.json()
        answer = result.get("answer", "")
        route = result.get("route", "")
        
        # Check route
        if test_case.get("expected_route"):
            if route != test_case["expected_route"]:
                return {
                    "name": test_case["name"],
                    "status": "FAIL",
                    "reason": f"Route mismatch: got '{route}', expected '{test_case['expected_route']}'"
                }
        
        # Check expected content
        if test_case.get("expected_content"):
            for content in test_case["expected_content"]:
                if content not in answer:
                    return {
                        "name": test_case["name"],
                        "status": "FAIL",
                        "reason": f"Missing expected content: '{content}'"
                    }
        
        # Check should not contain
        if test_case.get("should_not_contain"):
            for content in test_case["should_not_contain"]:
                if content in answer:
                    return {
                        "name": test_case["name"],
                        "status": "FAIL",
                        "reason": f"Contains forbidden content: '{content}'"
                    }
        
        return {
            "name": test_case["name"],
            "status": "PASS",
            "route": route,
            "answer_preview": answer[:100]
        }
        
    except Exception as e:
        return {
            "name": test_case["name"],
            "status": "ERROR",
            "reason": str(e)
        }

def main():
    print("=" * 60)
    print("Expert Explainer Routing Logic Test Suite")
    print("=" * 60)
    print()
    
    results = []
    for test_case in TEST_CASES:
        print(f"Testing: {test_case['name']}...")
        result = test_query(test_case)
        results.append(result)
        
        if result["status"] == "PASS":
            print(f"  ✅ PASS (route: {result.get('route')})")
        else:
            print(f"  ❌ {result['status']}: {result.get('reason')}")
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"Total: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print()
    
    if failed > 0 or errors > 0:
        print("Failed/Error Tests:")
        for r in results:
            if r["status"] != "PASS":
                print(f"  - {r['name']}: {r.get('reason')}")
    
    return 0 if (failed == 0 and errors == 0) else 1

if __name__ == "__main__":
    exit(main())
