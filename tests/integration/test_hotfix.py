"""
Quick Test Script for Production Hotfix Verification
Tests the 5 core scenarios specified by user.
"""

import sys
import os
sys.path.append(os.getcwd())

import yaml
from src.core.chat_engine import ChatEngine

def test_hotfix():
    config_path = "configs/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    engine = ChatEngine(config)
    
    test_cases = [
        {"input": "zte sw command", "expect_route": "article_link_only_exact"},
        {"input": "ZTE__SW__Command", "expect_route": "article_link_only_exact"},
        {"input": "Command NCS", "expect_route": "article_answer"},  # Not exact title
        {"input": "Cisco OLT new command", "expect_route": "blocked_vendor_out_of_scope"},
        {"input": "Juniper router config", "expect_route": "blocked_vendor_out_of_scope"},
    ]
    
    print("🔧 Production Hotfix Verification\n")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        inp = tc["input"]
        expected = tc["expect_route"]
        
        print(f"\n🧪 Testing: '{inp}'")
        res = engine.process(inp)
        
        actual_route = res.get("route")
        decision_reason = res.get("decision_reason") or res.get("audit", {}).get("decision_reason")
        
        # Check 1: Route matches
        route_ok = actual_route == expected
        
        # Check 2: decision_reason is not None
        reason_ok = decision_reason is not None and decision_reason != "None" and decision_reason != ""
        
        # Check 3: For exact matches, route MUST be article_link_only_exact
        if "zte sw command" in inp.lower() and "cisco" not in inp.lower():
            exact_ok = actual_route == "article_link_only_exact"
        else:
            exact_ok = True
        
        status = "✅ PASS" if (route_ok and reason_ok and exact_ok) else "❌ FAIL"
        
        print(f"   Route: {actual_route} (Expected: {expected}) {'✅' if route_ok else '❌'}")
        print(f"   Decision Reason: {decision_reason} {'✅' if reason_ok else '❌'}")
        
        if status == "✅ PASS":
            passed += 1
        else:
            failed += 1
            if not route_ok:
                print(f"   ❌ Route mismatch")
            if not reason_ok:
                print(f"   ❌ Decision reason is None/empty")
            if not exact_ok:
                print(f"   ❌ Exact match didn't route to LINK_ONLY")
        
        print(f"   {status}")
    
    print("\n" + "="*60)
    print(f"📊 SUMMARY: {passed}/{len(test_cases)} Passed")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    test_hotfix()
