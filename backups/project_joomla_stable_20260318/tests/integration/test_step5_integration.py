"""
Test Step 5: Clarification Gate Integration
Tests that ambiguous queries trigger clarification, specific queries pass through.
"""

import sys
import os
sys.path.append(os.getcwd())

import yaml
from src.core.chat_engine import ChatEngine

config = yaml.safe_load(open('configs/config.yaml'))
engine = ChatEngine(config)

def test_step5_integration():
    print("🧪 Testing Step 5: Clarification Gate Integration\n")
    print("="*70)
    
    test_cases = [
        {
            "query": "คำสั่งHuawei",
            "expected_route": "pending_clarification",
            "description": "Broad vendor command → should request clarification"
        },
        {
            "query": "Huawei command",
            "expected_route": "pending_clarification",
            "description": "Generic command query → should request clarification"
        },
        {
            "query": "Huawei add vlan",
            "expected_route_not": "pending_clarification",
            "description": "Specific command → should pass through normally"
        },
        {
            "query": "ZTE-SW Command",
            "expected_route": "article_link_only_exact",
            "description": "Exact title match → should bypass ambiguity check"
        }
    ]
    
    passed = 0
    for tc in test_cases:
        query = tc["query"]
        print(f"\nQuery: '{query}'")
        print(f"Expected: {tc['description']}")
        
        result = engine.process(query)
        route = result.get("route")
        answer = result.get("answer", "")
        
        print(f"Route: {route}")
        
        # Check expectations
        success = False
        if "expected_route" in tc:
            if route == tc["expected_route"]:
                print("✅ PASS - Route matches")
                success = True
            else:
                print(f"❌ FAIL - Expected {tc['expected_route']}, got {route}")
        elif "expected_route_not" in tc:
            if route != tc["expected_route_not"]:
                print(f"✅ PASS - Did not route to {tc['expected_route_not']}")
                success = True
            else:
                print(f"❌ FAIL - Incorrectly routed to {tc['expected_route_not']}")
        
        if success:
            passed += 1
        
        # Show answer preview
        if route == "pending_clarification":
            print(f"Clarification message: {answer[:150]}...")
    
    print("\n" + "="*70)
    print(f"Results: {passed}/{len(test_cases)} passed")
    
    return 0 if passed == len(test_cases) else 1

if __name__ == "__main__":
    exit(test_step5_integration())
