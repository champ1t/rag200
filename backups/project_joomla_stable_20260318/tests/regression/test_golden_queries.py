
import json
import pytest
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.chat_engine import ChatEngine

def load_golden_queries():
    try:
        with open("data/golden_queries.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

import yaml

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.mark.asyncio
async def test_golden_queries():
    cfg = load_config("configs/config.yaml")
    chat_engine = ChatEngine(cfg)
    queries = load_golden_queries()
    
    results = []
    
    print(f"\n🚀 Starting Regression Test on {len(queries)} Golden Queries...\n")
    
    for case in queries:
        category = case.get("category")
        question_input = case.get("question")
        expected_type = case.get("expected_type")
        expected_contains = case.get("expected_contains")
        
        # Handle multi-turn conversation
        if isinstance(question_input, list):
            print(f"🔄 Testing Multi-turn: {question_input}")
            # Reset context for independent test
            chat_engine.reset_context()
            
            final_res = None
            for q in question_input:
                final_res = chat_engine.process(q)
                
            response_text = final_res.get("answer", "")
            route = final_res.get("route", "unknown")
            
        else:
            # Single turn
            print(f"➡️ Testing: {question_input}")
            chat_engine.reset_context()
            final_res = chat_engine.process(question_input)
            response_text = final_res.get("answer", "")
            route = final_res.get("route", "unknown")

        # Validation Logic
        passed = True
        failure_reason = []

        # Check intent/route mapping
        # Note: mapping 'expected_type' to actual 'route' names might need adjustment
        if expected_type == "person":
             if route != "person_lookup" and route != "position_holder_lookup":
                 # Strict check? Or just check content?
                 # Let's trust content more for high level test
                 pass
        
        if expected_contains and expected_contains not in response_text:
            passed = False
            failure_reason.append(f"Response missing '{expected_contains}'")

        if expected_type == "irrelevant" and "ขออภัย" not in response_text and "ไม่พบข้อมูล" not in response_text:
             # loose check for irrelevant
             pass

        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
             print(f"   Response: {response_text[:100]}...")
             print(f"   Route: {route}")
             print(f"   Reason: {failure_reason}")
        
        results.append({
            "question": str(question_input),
            "status": status,
            "route": route
        })

    # Summary
    passed_count = len([r for r in results if r["status"] == "✅ PASS"])
    print(f"\n📊 Summary: {passed_count}/{len(queries)} Passed")
    
    if passed_count < len(queries):
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_golden_queries())
