#!/usr/bin/env python3
"""
System Health Check - Test current state after context memory changes
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.core.chat_engine import ChatEngine
from pathlib import Path
import yaml

print("=" * 80)
print("SYSTEM HEALTH CHECK - Context Memory Changes")
print("=" * 80)

# Load config
config_path = Path("/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Initialize engine
print("\n[1] Initializing ChatEngine...")
try:
    engine = ChatEngine(config)
    print("✅ ChatEngine initialization: OK")
except Exception as e:
    print(f"❌ ChatEngine initialization: FAILED - {e}")
    sys.exit(1)

# Test cases
test_cases = [
    {
        "name": "Basic Contact Query",
        "query": "เบอร์ CSOC",
        "expected_route": "contact",
        "should_work": True
    },
    {
        "name": "Team Query",
        "query": "สมาชิก helpdesk",
        "expected_route": "team",
        "should_work": True
    },
    {
        "name": "Tech Article",
        "query": "config vlan",
        "expected_route": "article",
        "should_work": True
    },
    {
        "name": "Context Enrichment (Simple)",
        "queries": ["เบอร์ CSOC", "ขอเบอร์"],
        "check_context": True,
        "should_work": "partial"  # Enrichment works, but may not preserve intent
    }
]

results = []

print("\n[2] Running Basic Tests...")
print("-" * 80)

for i, test in enumerate(test_cases[:3], 1):  # Basic tests only
    print(f"\nTest {i}: {test['name']}")
    print(f"Query: '{test['query']}'")
    
    try:
        result = engine.process(test['query'])
        route = result.get('route', 'unknown')
        answer = result.get('answer', '')[:100]
        
        # Check if it worked
        worked = result.get('route') is not None and len(answer) > 0
        status = "✅ PASS" if worked else "❌ FAIL"
        
        print(f"  Route: {route}")
        print(f"  Answer: {answer}...")
        print(f"  Status: {status}")
        
        results.append({
            "test": test['name'],
            "status": "PASS" if worked else "FAIL",
            "route": route
        })
        
        engine.clear_session()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        results.append({
            "test": test['name'],
            "status": "ERROR",
            "error": str(e)
        })

print("\n[3] Running Context Enrichment Test...")
print("-" * 80)

test = test_cases[3]
print(f"\nTest 4: {test['name']}")

try:
    # Query 1
    q1 = test['queries'][0]
    print(f"Q1: '{q1}'")
    result1 = engine.process(q1)
    print(f"  Route: {result1.get('route')}")
    print(f"  Answer: {result1.get('answer', '')[:80]}...")
    
    # Check context
    has_context = engine.last_context is not None
    print(f"  Context saved: {'✅ YES' if has_context else '❌ NO'}")
    if has_context:
        entities = engine.last_context.get('entities', {})
        print(f"  Entities: {list(entities.keys()) if entities else 'None'}")
    
    # Query 2
    q2 = test['queries'][1]
    print(f"\nQ2: '{q2}'")
    result2 = engine.process(q2)
    print(f"  Route: {result2.get('route')}")
    print(f"  Answer: {result2.get('answer', '')[:80]}...")
    
    # Overall status
    enrichment_worked = "CONTEXT" in str(result2.get('debug', ''))
    context_saved = has_context
    
    if enrichment_worked and context_saved:
        status = "✅ PARTIAL (enrichment works, intent may not preserve)"
    elif enrichment_worked:
        status = "⚠️ PARTIAL (enrichment works, no context save)"
    else:
        status = "❌ FAIL (no enrichment)"
    
    print(f"\n  Overall: {status}")
    
    results.append({
        "test": test['name'],
        "status": "PARTIAL" if enrichment_worked else "FAIL",
        "enrichment": enrichment_worked,
        "context_saved": context_saved
    })
    
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    results.append({
        "test": test['name'],
        "status": "ERROR",
        "error": str(e)
    })

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r['status'] == 'PASS')
partial = sum(1 for r in results if r['status'] == 'PARTIAL')
failed = sum(1 for r in results if r['status'] in ['FAIL', 'ERROR'])

print(f"\n✅ Passed: {passed}")
print(f"⚠️  Partial: {partial}")
print(f"❌ Failed: {failed}")

print("\nDetailed Results:")
for r in results:
    status_icon = {"PASS": "✅", "PARTIAL": "⚠️", "FAIL": "❌", "ERROR": "❌"}
    icon = status_icon.get(r['status'], "?")
    print(f"  {icon} {r['test']}: {r['status']}")

print("\n" + "=" * 80)

if failed == 0:
    print("✅ SYSTEM HEALTH: GOOD (no critical failures)")
    print("   Core functionality intact, context enrichment partially working")
    sys.exit(0)
else:
    print("❌ SYSTEM HEALTH: DEGRADED (failures detected)")
    sys.exit(1)
