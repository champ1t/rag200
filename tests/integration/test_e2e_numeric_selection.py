#!/usr/bin/env python3
"""
End-to-End Test: Numeric Selection with Chat Engine

Simulates the full flow:
1. Query: "คำสั่ง huawei"
2. System should show global numbered list (1-10)
3. User types: "1"
4. System should resolve to first article
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

# Set environment variable to suppress some warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Import ChatEngine
import yaml
from pathlib import Path

print("=" * 70)
print("End-to-End Test: Numeric Selection")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/config/rag_config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

print("\n[Step 1: Initialize ChatEngine]")
from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)
print("✅ ChatEngine initialized")
print(f"✅ Numeric Selection Resolver loaded: {engine.numeric_selection_resolver is not None}")
print(f"✅ Numeric Input Detector loaded: {engine.numeric_input_detector is not None}")

# Test 1: Query for vendor list
print("\n" + "=" * 70)
print("[Step 2: Query 'คำสั่ง huawei' - Should show numbered list]")
print("=" * 70)

result1 = engine.query("คำสั่ง huawei")
answer1 = result1.get('answer', '')

print(f"\nRoute: {result1.get('route')}")
print(f"Answer:\n{answer1}\n")

# Check for global numbering
has_numbers = any(str(i) + "." in answer1 for i in range(1, 11))
has_categories = "[Configuration]" in answer1 or "[ทั่วไป]" in answer1

if has_numbers and not has_categories:
    print("✅ Global numbering detected (no category headers)")
    print(f"✅ Pending session created: {engine.pending_numeric_session is not None}")
    
    if engine.pending_numeric_session:
        print(f"   Session ID: {engine.pending_numeric_session.get('session_id')}")
        print(f"   Max Number: {engine.pending_numeric_session.get('max_number')}")
        
        # Test 2: Select number 1
        print("\n" + "=" * 70)
        print("[Step 3: Type '1' - Should resolve to first article]")
        print("=" * 70)
        
        result2 = engine.query("1")
        answer2 = result2.get('answer', '')
        
        print(f"\nRoute: {result2.get('route')}")
        print(f"Answer:\n{answer2}\n")
        
        if result2.get('route') == 'numeric_selection_resolved':
            print("✅ Numeric selection resolved successfully")
            print(f"✅ Session cleared: {engine.pending_numeric_session is None}")
            
            # Test 3: Try invalid number
            print("\n" + "=" * 70)
            print("[Step 4: Query again and type '99' - Should show error]")
            print("=" * 70)
            
            result3 = engine.query("คำสั่ง huawei")
            result4 = engine.query("99")
            answer4 = result4.get('answer', '')
            
            print(f"\nRoute: {result4.get('route')}")
            print(f"Answer:\n{answer4}\n")
            
            if result4.get('route') == 'numeric_selection_invalid':
                print("✅ Invalid selection handled correctly")
                print(f"✅ Session preserved: {engine.pending_numeric_session is not None}")
                
                print("\n" + "=" * 70)
                print("✅ ALL END-TO-END TESTS PASSED")
                print("=" * 70)
            else:
                print("❌ Invalid selection test failed")
        else:
            print(f"❌ Selection not resolved. Route: {result2.get('route')}")
    else:
        print("❌ No session created")
elif has_categories:
    print("❌ Still showing category headers (old format)")
    print("   Expected: 1. config VAS...")
    print(f"   Got: {answer1[:200]}")
else:
    print("⚠️  Unexpected format")

print("\n" + "=" * 70)
