"""
Quick debug: Why entity matching doesn't work in live system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.context.context_manager import enrich_query_with_context, get_context_entities, create_context

# Simulate EXACT context from live system
# This is what chat_engine.py creates after Q1
live_context = create_context(
    query="ศูนย์หาดใหญ่โทรอะไร",
    intent="CONTACT_LOOKUP",
    route="contact",
    entities={
        "ศูนย์ OMC หาดใหญ่": "CONTACT",
        "ศูนย์ RNOC หาดใหญ่": "CONTACT"
    },
    result_data=[
        {"name": "ศูนย์ OMC หาดใหญ่", "phones": ["074-251-135"]},
        {"name": "ศูนย์ RNOC หาดใหญ่", "phones": ["074-856-174", "081-417-0144"]}
    ]
)

print("=" * 70)
print("LIVE SYSTEM SIMULATION")
print("=" * 70)

print("\n[Step 1: Context Created]")
print(f"entities: {live_context.get('entities')}")
print(f"data: {live_context.get('data')}")

print("\n[Step 2: Extract Entities]")
extracted = get_context_entities(live_context)
print(f"Extracted entities: {extracted}")

print("\n[Step 3: Enrich Query]")
query = "ของ RNOC ละ"
result = enrich_query_with_context(query, live_context)
print(f"Input:  '{query}'")
print(f"Output: '{result}'")

print("\n" + "=" * 70)
if "RNOC" in result and "ศูนย์ RNOC หาดใหญ่" in result:
    print("✅ SUCCESS - RNOC matched correctly!")
else:
    print(f"❌ FAILURE - Still selecting wrong entity")
    print(f"   Expected: 'ของ RNOC ละ ศูนย์ RNOC หาดใหญ่'")
    print(f"   Got:      '{result}'")
