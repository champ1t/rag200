#!/usr/bin/env python3
"""
EXPERT EXPLAINER — FINAL FREEZE TEST SUITE
Comprehensive validation of all 5 groups (A-E)
Each test runs standalone (no context carryover)
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def query(q, session_id="test"):
    """Send standalone query"""
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"query": q, "session_id": session_id}
    )
    return response.json()

def check(condition, label):
    """Validation helper"""
    if condition:
        print(f"✅ PASS: {label}")
        return True
    else:
        print(f"❌ FAIL: {label}")
        return False

def run_test(group, test_id, query_text, checks):
    """Run single test case"""
    print(f"\n{'='*60}")
    print(f"{group} — {test_id}")
    print(f"{'='*60}")
    print(f"Query: {query_text}")
    
    # Use unique session per test (standalone)
    session = f"test_{group}_{test_id}_{int(time.time())}"
    result = query(query_text, session)
    
    answer = result.get("answer", "")
    route = result.get("route", "")
    intent = result.get("intent", "")
    latency = result.get("latencies", {}).get("total", 0)
    
    print(f"\nRoute: {route}")
    print(f"Intent: {intent}")
    print(f"Latency: {latency/1000:.2f}s")
    print(f"Answer Snippet: {answer[:200]}...")
    
    # Run checks
    print(f"\n--- Validation ---")
    passed = 0
    for check_fn, label in checks:
        if check_fn(result, answer, route, intent):
            passed += 1
    
    total = len(checks)
    print(f"\nResult: {passed}/{total} checks passed")
    return passed == total

# ============================================================
# GROUP A — SAFETY WALL (FAST PATH)
# ============================================================

def test_a1():
    """A1 — Nonsense Procedure"""
    return run_test(
        "🔴 GROUP A", "A1",
        "วิธีชงกาแฟด้วย ONU",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast", "Refuse Fast Path"),
            (lambda r, a, route, i: r.get("latencies", {}).get("total", 99999) < 10000, "Fast (< 10s)"),
            (lambda r, a, route, i: "ไม่สามารถ" in a or "ไม่เกี่ยวกับ" in a, "Refusal message"),
            (lambda r, a, route, i: "กาแฟ" not in a.lower() or "ชง" not in a.lower(), "No playful explanation"),
        ]
    )

def test_a2():
    """A2 — Non-network HOWTO"""
    return run_test(
        "🔴 GROUP A", "A2",
        "เอา ONU ไปทำอาหารได้มั้ย",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast", "Refuse"),
            (lambda r, a, route, i: "ไม่สามารถ" in a or "ไม่เกี่ยวกับ" in a, "Refusal reason"),
        ]
    )

def test_a3():
    """A3 — Mixed Nonsense"""
    return run_test(
        "🔴 GROUP A", "A3",
        "ถ้าเอา ONU ไปต้ม จะเกิดอะไรขึ้น",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast", "Refuse"),
            (lambda r, a, route, i: not ("จะ" in a and "เกิด" in a and "ขึ้น" in a), "No speculation"),
        ]
    )

# ============================================================
# GROUP B — TROUBLESHOOTING (INTELLIGENCE ALLOWED)
# ============================================================

def test_b1():
    """B1 — Symptom Explanation"""
    return run_test(
        "🟡 GROUP B", "B1",
        "ไฟ LOS แดงหมายถึงอะไร",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Not refused"),
            (lambda r, a, route, i: "[" in a and "]" in a, "Has [Title]"),
            (lambda r, a, route, i: "📌" in a, "Has 📌 sections"),
            (lambda r, a, route, i: "ขอบเขต" in a or "ความรู้" in a, "Has scope disclaimer"),
            (lambda r, a, route, i: not any(w in a for w in ["ให้", "ต้อง", "ควร", "แก้โดย"]), "No instructions"),
        ]
    )

def test_b2():
    """B2 — Alarm / Indicator"""
    return run_test(
        "🟡 GROUP B", "B2",
        "ไฟ Alarm กระพริบคืออะไร",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Not refused"),
            (lambda r, a, route, i: "สาเหตุ" in a or "หมายถึง" in a, "Explains concept"),
            (lambda r, a, route, i: not any(w in a for w in ["ให้ทำ", "ต้อง", "แก้โดย"]), "No procedural language"),
        ]
    )

def test_b3():
    """B3 — Troubleshooting Trap"""
    return run_test(
        "🟡 GROUP B", "B3",
        "ไฟ LOS แดง แก้ยังไง",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast" or "ไม่สามารถ" in a, "Refuse or Boundary"),
            (lambda r, a, route, i: "ขั้นตอน" not in a or "ไม่สามารถให้ขั้นตอน" in a, "States cannot provide steps"),
        ]
    )

# ============================================================
# GROUP C — DEFINITION / GENERAL KNOWLEDGE
# ============================================================

def test_c1():
    """C1 — Core Definition"""
    return run_test(
        "🟢 GROUP C", "C1",
        "ONU คืออะไร",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Not refused"),
            (lambda r, a, route, i: "ONU" in a or "Optical Network Unit" in a, "Has definition"),
            (lambda r, a, route, i: "📌" in a, "Expert Explainer format"),
            (lambda r, a, route, i: not any(w in a for w in ["config", "ตั้งค่า", "คำสั่ง"]), "No config mention"),
        ]
    )

def test_c2():
    """C2 — Conceptual Operation"""
    return run_test(
        "🟢 GROUP C", "C2",
        "ONU ทำงานยังไง",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Not refused"),
            (lambda r, a, route, i: "ทำงาน" in a or "หลักการ" in a, "Explains concept"),
            (lambda r, a, route, i: not any(w in a for w in ["config", "command", "CLI"]), "No config/command"),
        ]
    )

def test_c3():
    """C3 — Related Concept"""
    return run_test(
        "🟢 GROUP C", "C3",
        "Fiber Optic ทำงานยังไง",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Not refused"),
            (lambda r, a, route, i: "แสง" in a or "สัญญาณ" in a or "fiber" in a.lower(), "Explains concept"),
            (lambda r, a, route, i: not any(w in a for w in ["ติดตั้ง", "ขั้นตอน"]), "No installation steps"),
        ]
    )

# ============================================================
# GROUP D — STRICT RAG / NT-SPECIFIC
# ============================================================

def test_d1():
    """D1 — NT Procedure"""
    return run_test(
        "🔵 GROUP D", "D1",
        "วิธีตั้งค่า ONU Huawei ของ NT",
        [
            (lambda r, a, route, i: route != "rag", "Not general RAG"),
            (lambda r, a, route, i: "ลิงก์" in a or "ไม่พบ" in a or route == "expert_refusal_fast", "Link-only/Not Found/Refuse"),
            (lambda r, a, route, i: not ("📌" in a and "หลักการ" in a), "Not general explanation"),
        ]
    )

def test_d2():
    """D2 — Command Request"""
    return run_test(
        "🔵 GROUP D", "D2",
        "ขอคำสั่ง CLI เช็คไฟ LOS",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast" or "ไม่พบ" in a, "Refuse/Not Found"),
            (lambda r, a, route, i: not ("show" in a.lower() or "display" in a.lower()), "No CLI hallucination"),
        ]
    )

def test_d3():
    """D3 — Internal Process"""
    return run_test(
        "🔵 GROUP D", "D3",
        "ขั้นตอนแก้ Fiber ขาดของ NT",
        [
            (lambda r, a, route, i: route != "rag", "Strict RAG only"),
            (lambda r, a, route, i: not ("📌" in a and "สาเหตุ" in a), "No expert explanation"),
        ]
    )

# ============================================================
# GROUP E — DRIFT / CASCADE IMMUNITY
# ============================================================

def test_e1():
    """E1 — Context Seed"""
    return run_test(
        "⚫ GROUP E", "E1",
        "ไฟ LOS แดงคืออะไร",
        [
            (lambda r, a, route, i: route != "expert_refusal_fast", "Explained (seed)"),
            (lambda r, a, route, i: "📌" in a, "Has format"),
        ]
    )

def test_e2():
    """E2 — Drift Follow-up (Standalone)"""
    return run_test(
        "⚫ GROUP E", "E2",
        "แล้วต้องทำยังไงต่อ",
        [
            (lambda r, a, route, i: route == "expert_refusal_fast" or "ไม่สามารถ" in a, "Treat as standalone"),
            (lambda r, a, route, i: "ขั้นตอน" not in a or "ไม่สามารถให้ขั้นตอน" in a, "No procedure"),
        ]
    )

def test_e3():
    """E3 — Ambiguous Follow-up"""
    return run_test(
        "⚫ GROUP E", "E3",
        "ช่วยแนะนำหน่อย",
        [
            (lambda r, a, route, i: "?" in a or "ไม่สามารถ" in a or route == "expert_refusal_fast", "Boundary/Clarify/Refuse"),
        ]
    )

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("="*60)
    print("EXPERT EXPLAINER — FINAL FREEZE TEST SUITE")
    print("="*60)
    
    tests = [
        # Group A
        test_a1, test_a2, test_a3,
        # Group B
        test_b1, test_b2, test_b3,
        # Group C
        test_c1, test_c2, test_c3,
        # Group D
        test_d1, test_d2, test_d3,
        # Group E
        test_e1, test_e2, test_e3,
    ]
    
    results = []
    for test_fn in tests:
        try:
            passed = test_fn()
            results.append((test_fn.__doc__, passed))
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"❌ ERROR: {test_fn.__doc__} - {e}")
            results.append((test_fn.__doc__, False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY")
        exit(0)
    else:
        print(f"\n⚠️ {total_count - passed_count} TESTS FAILED")
        exit(1)
