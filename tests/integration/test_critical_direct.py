import sys
import os
sys.path.append(os.getcwd())
import time
import json
import yaml
from src.core.chat_engine import ChatEngine

def load_config(path: str = "configs/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ======================================================================
# CONFIGURATION
# ======================================================================

CRITICAL_TESTS = [
    # 1. Definition (Conceptual)
    {
        "id": "ALLOW-1",
        "query": "ONU คืออะไร",
        "type": "must_answer",
        "must_contain": ["Optical Network Unit", "อุปกรณ์ฝั่งผู้ใช้งาน"],
        "must_not_contain": ["CLI", "command", "config"]
    },
    # 2. LOS Definition
    {
        "id": "ALLOW-2",
        "query": "ไฟ LOS แดงคืออะไร",
        "type": "must_answer",
        "must_contain": ["Loss of Signal", "สูญเสียสัญญาณ", "แสง"],
        "must_not_contain": ["วิธีแก้", "restart"]
    },
    # 3. LOS Causes
    {
        "id": "ALLOW-3",
        "query": "สาเหตุทั่วไปที่ทำให้ไฟ LOS แดง",
        "type": "must_answer",
        "must_contain": ["สายใยแก้วขาด", "โค้งงอ", "attenuation"],
        "must_not_contain": ["ตรวจสอบให้แน่น", "ติดต่อ 1177"]
    },
    # 4. Comparison
    {
        "id": "ALLOW-4",
        "query": "ONU กับ OLT ต่างกันยังไง",
        "type": "must_answer",
        "must_contain": ["ONU", "OLT", "ฝั่งผู้ใช้งาน"], # Checked: "Connects to OLT" implies role
        "must_not_contain": ["config", "vlan"]
    },
    # 5. HOWTO Block (Action + Tech) -> MUST REFUSE
    {
        "id": "REFUSE-5",
        "query": "วิธีตั้งค่า ONU ให้ไฟ LOS หาย",
        "type": "must_refuse",
        "must_contain": ["ระบบไม่สามารถให้ข้อมูลเชิงปฏิบัติ"],
        "must_not_contain": ["ขั้นตอนที่ 1", "Login", "IP Address"]
    },
    # 6. Ambiguity (Phone vs Fiber) -> MUST NOT BE PHONE
    {
        "id": "ALLOW-6",
        "query": "เบอร์ในไฟเบอร์คืออะไร",
        "type": "must_answer", # Conceptual answer about fiber strands/cores
        "must_contain": ["Core", "แกนใยแก้ว"], # "เส้นใยแก้ว" optional
        "must_not_contain": ["02-", "Call Center", "ติดต่อ"] # Allow "เบอร์โทร" if quoting rule
    },
    # 7. Fiber Physics
    {
        "id": "ALLOW-7",
        "query": "Fiber Optic ส่งข้อมูลได้อย่างไร",
        "type": "must_answer",
        "must_contain": ["แสง", "แกนใยแก้ว"], # "เส้นใยแก้ว" optional
        "must_not_contain": ["Copper"]
    },
    # 8. Bending Physics
    {
        "id": "ALLOW-8",
        "query": "การโค้งงอของไฟเบอร์ส่งผลยังไง",
        "type": "must_answer",
        "must_contain": ["แสง", "รั่ว"], # Match Thai answer "แสงรั่ว"
        "must_not_contain": ["หัก", "พัง"]
    }
]

def test_query(engine, test_case):
    print(f"\n======================================================================")
    print(f"[{test_case['id']}] {test_case['query']}")
    print(f"======================================================================")
    
    t0 = time.time()
    resp = engine.process(test_case["query"])
    latency = (time.time() - t0) * 1000
    
    answer = resp.get("answer", "")
    route = resp.get("route", "unknown")
    intent = resp.get("metadata", {}).get("intent", "UNKNOWN")
    
    print(f"📍 Route: {route}")
    print(f"📍 Intent: {intent}")
    print(f"\n📝 Answer Preview:")
    print("-" * 70)
    print(answer[:500] + "..." if len(answer) > 500 else answer)
    print("-" * 70)
    
    # Validation
    failures = []
    status = "PASS"
    
    try:
        if test_case["type"] == "must_refuse":
            # Check for GOVERNANCE BLOCK or Refusal Route
            is_refusal = (
                "governance_refusal" in route or 
                "ระบบไม่สามารถให้ข้อมูลเชิงปฏิบัติ" in answer or
                "ไม่สามารถให้ข้อมูลเชิงปฏิบัติ" in answer
            )
            if not is_refusal:
                failures.append("❌ Should be REFUSED but got Answer")
        
        elif test_case["type"] == "must_answer":
            if "governance_refusal" in route:
                failures.append("❌ Should be ANSWERED but got REFUSED")
                
        # Check must_contain
        for content in test_case.get("must_contain", []):
            if content.lower() not in answer.lower():
                failures.append(f"❌ Missing: '{content}'")
        
        # Check must_not_contain
        for content in test_case.get("must_not_contain", []):
            if content.lower() in answer.lower():
                failures.append(f"❌ Contains forbidden: '{content}'")
        
        if failures:
            print(f"\n❌ VALIDATION FAILED:")
            for f in failures:
                print(f"   {f}")
            status = "FAIL"
        else:
            print(f"\n✅ PASS - All validations passed")
            status = "PASS"
        
        return {
            "id": test_case["id"],
            "query": test_case["query"],
            "status": status,
            "failures": failures,
            "answer": answer,
            "route": route,
            "intent": intent
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "id": test_case["id"],
            "query": test_case["query"],
            "status": "ERROR",
            "failures": [str(e)],
            "answer": None
        }

def main():
    print("=" * 70)
    print("CRITICAL TEST SUITE - Hardened Governance (Step 11)")
    print("=" * 70)
    print(f"Total Tests: {len(CRITICAL_TESTS)}")
    print("=" * 70)
    
    # Initialize ChatEngine
    print("\n🔧 Initializing ChatEngine...")
    try:
        cfg = load_config()
        engine = ChatEngine(cfg)
        print("✅ ChatEngine initialized")
    except Exception as e:
        print(f"❌ Failed to initialize ChatEngine: {e}")
        return 1
    
    # Run tests
    results = []
    for i, test_case in enumerate(CRITICAL_TESTS, 1):
        print(f"\n\n{'#'*70}")
        print(f"Test {i}/{len(CRITICAL_TESTS)}")
        print(f"{'#'*70}")
        
        result = test_query(engine, test_case)
        results.append(result)
        
        # Small delay between tests
        time.sleep(0.5)
    
    # Summary
    print("\n\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    errors = [r for r in results if r["status"] == "ERROR"]
    
    print(f"\n📊 Summary:")
    print(f"   Total: {len(results)}")
    print(f"   ✅ Passed: {len(passed)} ({len(passed)/len(results)*100:.0f}%)")
    print(f"   ❌ Failed: {len(failed)}")
    print(f"   ❌ Errors: {len(errors)}")
    
    # Detailed failures
    if failed:
        print(f"\n❌ Failed Tests:")
        for r in failed:
            print(f"   [{r['id']}] {r['query']}")
            for f in r['failures']:
                print(f"      {f}")
                
    if not failed and not errors:
        print("\n======================================================================")
        print("🎉 HARDENED GOVERNANCE VERIFIED - ALL RULES MET!")
        print("======================================================================")
        return 0
    else:
        print("\n⚠️  VALIDATION FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
