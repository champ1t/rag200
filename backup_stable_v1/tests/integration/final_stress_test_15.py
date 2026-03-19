import requests
import json
import time

BASE_URL = "http://localhost:8000/chat"
HEADERS = {"X-API-Key": "nt-rag-secret", "Content-Type": "application/json"}
SESSION_ID = "stress_test_174_final"

LONG_TEXT = "Test content " * 300  # ~3300 chars

TEST_CASES = [
    # Group 1: Long Articles
    ("TR069 CWMP Setting", "article_answer"),
    ("วิธีแก้ TR069 ที่ลูกค้าออนไลน์หลุดบ่อย", "article_answer_with_synonym"),
    ("ข้อจำกัดของ NCS", "article_answer"),
    # Group 2: Tables / Junk Stress
    ("Huawei fttx มีปัญหา speed ตก", "article_answer"),
    ("IP_SSH", "article_answer"),
    # Group 3: Directory / Nav
    ("ตาราง proxy IP PHONE", "needs_choice"),
    ("คู่มือปฏิบัติงาน 1177 ภาคใต้", "needs_choice"),
    # Group 4: Synonym / Rollback
    ("เข้าเว็บ edoc ไม่ได้", "article_answer"), # Should map to Edocument
    ("วิธีแก้ ipphone ไม่โอนเบอร์ภายใน", "article_answer"), 
    ("tr069 หลุดบ่อยทำยังไงดี", "article_answer"),
    # Group 5: Contact
    ("เบอร์ สื่อสารข้อมูล ภูเก็ต", "contact_hit"),
    ("เบอร์ Intra TOT", "contact_hit"),
    # Group 6: Edge / Safety
    ("", "greeting"), # Empty
    ("😂😂😂", "greeting"), # Emoji
    (LONG_TEXT, "truncated_processing") # Long
]

def run_stress_test():
    print(f"\n" + "!"*50)
    print("      PHASE 174 GLOBAL STRESS TEST (15 CASES)")
    print("!"*50 + "\n")
    
    results = []
    for i, (q, expected) in enumerate(TEST_CASES, 1):
        display_q = q[:50] + "..." if len(q) > 50 else (q if q else "(EMPTY)")
        print(f"[{i}/15] Testing: '{display_q}'")
        
        try:
            t0 = time.time()
            resp = requests.post(BASE_URL, json={"message": q, "session_id": SESSION_ID}, headers=HEADERS, timeout=45)
            dt = time.time() - t0
            
            if resp.status_code == 200:
                data = resp.json()
                route = data.get("route")
                answer = data.get("answer", "")
                has_source = len(data.get("sources", [])) > 0 or "แหล่งที่มา" in answer or "http" in answer
                has_title = "[" in answer[:50] and "]" in answer[:50]
                
                status = "PASS"
                # Heuristic check for Group 6
                if not q and "สวัสดี" in answer: status = "PASS (Greet)"
                
                print(f"      -> Route: {route} | Latency: {dt:.1f}s | Title: {'YES' if has_title else 'NO'} | Source: {'YES' if has_source else 'NO'}")
                results.append({
                    "id": i, "query": display_q, "route": route, "latency": dt, 
                    "has_title": has_title, "has_source": has_source, "ok": True
                })
            else:
                print(f"      -> FAILED (Status {resp.status_code})")
                results.append({"id": i, "query": display_q, "ok": False, "error": resp.status_code})
                
        except Exception as e:
            print(f"      -> ERROR: {e}")
            results.append({"id": i, "query": display_q, "ok": False, "error": str(e)})

    print("\n" + "="*50)
    print("      STRESS TEST SUMMARY")
    print("="*50)
    passed = sum(1 for r in results if r.get("ok"))
    print(f"Total: {len(results)} | Passed (Success Code): {passed}/15")
    
if __name__ == "__main__":
    run_stress_test()
