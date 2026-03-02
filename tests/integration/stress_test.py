import requests
import json
import time

API_URL = "http://localhost:8000/chat"
HEADERS = {
    "X-API-Key": "nt-rag-secret",
    "Content-Type": "application/json"
}

# 1. HAT Simulation Queries (Naive User)
HAT_QUERIES = [
    {"q": "เบอร์ติดต่อ ภูเก็ต", "desc": "Naive Contact"},
    {"q": "วิธีแก้ TR069", "desc": "Naive How-To"},
    {"q": "เข้าเว็บ Edoc", "desc": "Naive Link"}
]

# 2. Long Article Stress (Hypothetical Query)
# We expect "TR069 CWMP Setting" to be relatively long based on previous tests.
LONG_QUERY = "TR069 CWMP Setting"

def run_query(query, session="stress_test"):
    try:
        resp = requests.post(API_URL, json={
            "message": query,
            "user": "stress_tester",
            "session_id": session,
            "top_k": 3
        }, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def test_long_article():
    print("\n--- Long Article Stress Test ---")
    data = run_query(LONG_QUERY)
    
    if "answer" in data:
        ans = data["answer"]
        print(f"Title present?: {'[' in ans[:50]}")
        print(f"Length: {len(ans)} chars")
        print(f"Footer 'อ่านต่อ' present?: {'อ่านต่อ' in ans[-300:] or 'http' in ans[-300:]}")
        print("Start Preview:", ans[:100].replace('\n', ' '))
        print("End Preview:", ans[-100:].replace('\n', ' '))
        
        if len(ans) > 500 and "[" in ans[:50]:
            print("✅ PASS: Long structure valid")
        else:
            print("⚠️ WARN: Content might be too short or missing title")
    else:
        print("❌ FAIL: No answer")
        
    return data

def test_hat():
    print("\n--- HAT Simulation ---")
    for item in HAT_QUERIES:
        print(f"Asking: '{item['q']}' ...")
        data = run_query(item['q'])
        ans = data.get("answer", "")
        print(f"Response ({len(ans)} chars): {ans[:100]}...")
        if len(ans) > 20: 
            print("✅ OK (Readable)")
        else:
            print("⚠️ Suspiciously short")

if __name__ == "__main__":
    print("=== STARTING STRESS & SANITY TEST ===")
    test_long_article()
    test_hat()
