import requests
import json
import unicodedata

API_URL = "http://localhost:8000/chat"
HEADERS = {
    "X-API-Key": "nt-rag-secret",
    "Content-Type": "application/json"
}

TEST_CASES = [
    {
        "name": "TR069 Direct Preview",
        "query": "TR069 CWMP Setting",
        "expect_in_answer": ["[TR069 CWMP Setting]", "เนื้อหามีรายละเอียดเพิ่มเติม", "อ่านต่อฉบับเต็มได้ที่"],
        "expect_not_in_answer": ["1. | 133"] # Should NOT show the raw table index list (Fast Path)
    },
    {
        "name": "Ribbon Directory",
        "query": "Ribbon EdgeMare6000 DOC",
        "expect_in_answer": ["[Ribbon EdgeMare6000 DOC]", "EdgeView_16.0.1_User_Guide"],
        "min_answer_len": 50
    },
    {
        "name": "Table Cleaning (Huawei)",
        "query": "Huawei_fttx",
        "expect_in_answer": ["[Huawei_fttx]"],
        "expect_not_in_answer": ["| 51 | 123", "| 51 | 522"], # Should be cleaned or skipped
        "note": "Output must NOT start with stats table"
    },
    {
        "name": "JSON Sanitization (Phuket)",
        "query": "เบอร์ สื่อสารข้อมูล ภูเก็ต",
        "expect_valid_json": True, 
        "expect_in_answer": ["076"]
    },
    {
        "name": "Reference Link",
        "query": "ขอลิงก์ Edocument",
        "expect_in_answer": ["Edocument", "http"],
        "check_route": "article_answer"
    }
]

def run_tests():
    print("=== Running 5 Verification Tests (Strict) ===")
    results = []
    
    for case in TEST_CASES:
        print(f"\nTesting: {case['name']} ('{case['query']}') ...")
        try:
            resp = requests.post(API_URL, json={
                "message": case['query'], 
                "user": "verifier_strict", 
                "session_id": "verify_session_strict",
                "top_k": 3
            }, headers=HEADERS, timeout=10)
            
            if resp.status_code != 200:
                print(f"FAILED: Status {resp.status_code}")
                results.append((case['name'], False, f"HTTP {resp.status_code}"))
                continue
                
            data = resp.json()
            answer = data.get("answer", "")
            
            failed_reasons = []
            
            # Check Title Prepend (for Direct Preview cases)
            if "Direct Preview" in case['name'] or "Table Cleaning" in case['name']:
                 if not answer.strip().startswith("["):
                      failed_reasons.append("Answer does NOT start with [Title]")
            
            if "expect_in_answer" in case:
                for kw in case["expect_in_answer"]:
                    if kw not in answer:
                        failed_reasons.append(f"Missing keyword: '{kw}'")
            
            if "expect_not_in_answer" in case:
                for kw in case["expect_not_in_answer"]:
                    if kw in answer:
                        failed_reasons.append(f"Found forbidden keyword: '{kw}'")
                        
            if failed_reasons:
                print(f"FAILED: {', '.join(failed_reasons)}")
                print(f"Answer Start: '{answer[:50]}'")
                results.append((case['name'], False, failed_reasons))
            else:
                print("PASSED")
                preview = answer.replace('\n', ' ')[:80]
                print(f"Output: {preview}...")
                results.append((case['name'], True, "OK"))
                
        except Exception as e:
            print(f"ERROR: {e}")
            results.append((case['name'], False, str(e)))
            
    print("\n=== Summary ===")
    for name, passed, reason in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}: {reason}")

if __name__ == "__main__":
    run_tests()
