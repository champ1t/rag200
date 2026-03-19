"""
Test Step 2: Controlled Summary Mode
Tests that LLM summaries only happen for narrative content.
"""

import sys
import os
sys.path.append(os.getcwd())

import yaml
from src.core.chat_engine import ChatEngine

# Load config
config = yaml.safe_load(open('configs/config.yaml'))
engine = ChatEngine(config)

def test_step2():
    print("🧪 Testing Step 2: Controlled Summary Mode\n")
    print("="*70)
    
    test_cases = [
        {
            "query": "GPON Overview",
            "expected_behavior": "LLM summary (narrative content)",
            "check_summary": True,
            "check_link": True
        },
        {
            "query": "ZTE-SW Command",
            "expected_behavior": "Link only (non-narrative/command)",
            "check_summary": False,
            "check_link": True
        },
    ]
    
    for tc in test_cases:
        query = tc["query"]
        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print(f"Expected: {tc['expected_behavior']}")
        
        res = engine.process(query)
        
        route = res.get("route", "")
        answer = res.get("answer", "")
        content_type = res.get("content_type")
        decision_reason = res.get("decision_reason", "")
        
        print(f"\nRoute: {route}")
        print(f"Content Type: {content_type}")
        print(f"Decision Reason: {decision_reason}")
        print(f"\nAnswer preview (first 200 chars):")
        print(answer[:200])
        
        # Check expectations
        has_summary = len(answer) > 300 and "•" in answer  # Rough heuristic for summary
        has_link = "🔗" in answer or "http" in answer
        
        print(f"\nHas LLM summary: {has_summary}")
        print(f"Has link: {has_link}")
        
        if tc["check_summary"] and not has_summary:
            print("⚠️  Expected summary but didn't find one")
        elif not tc["check_summary"] and has_summary:
            print("⚠️  Found summary but expected link-only")
        else:
            print("✅ Behavior matches expectation")
    
    print("\n" + "="*70)
    print("Step 2 test complete")

if __name__ == "__main__":
    test_step2()
