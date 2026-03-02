"""
Test Content Classifier - Step 1
Tests rule-based article content classification without LLM.
"""

import sys
import os
sys.path.append(os.getcwd())

from src.ai.content_classifier import classify_article_content

def test_classifier():
    print("🧪 Testing Content Classifier (Step 1)\n")
    print("="*60)
    
    test_cases = [
        {
            "input": {"title": "ZTE-SW Command", "type": "OVERVIEW"},
            "expected": "index",  # OVERVIEW with "command" in title → index
            "description": "Command collection/index"
        },
        {
            "input": {"title": "vlan", "type": "COMMAND_REFERENCE"},
            "expected": "command_reference",
            "description": "Technical command reference"
        },
        {
            "input": {"title": "GPON Overview", "type": None},
            "expected": "index",  # "Overview" in title → index
            "description": "Overview article (no article_type)"
        },
        {
            "input": {"title": "ONU Command", "type": None},
            "expected": "command_reference",  # "Command" in title → command_reference
            "description": "Command without article_type"
        },
        {
            "input": {"title": "OLT คืออะไร", "type": None},
            "expected": "narrative",
            "description": "Definition/concept question"
        },
        {
            "input": {"title": "Migration Guide", "type": "MIGRATION_CONVERSION"},
            "expected": "command_reference",
            "description": "Migration guide"
        },
    ]
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        inp = tc["input"]
        expected = tc["expected"]
        desc = tc["description"]
        
        result = classify_article_content(
            article_title=inp["title"],
            article_type=inp.get("type")
        )
        
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"\n{status} {desc}")
        print(f"   Title: '{inp['title']}'")
        print(f"   Type: {inp.get('type')}")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")
    
    print("\n" + "="*60)
    print(f"📊 Results: {passed}/{len(test_cases)} passed")
    
    if failed > 0:
        print(f"❌ {failed} tests failed")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    test_classifier()
