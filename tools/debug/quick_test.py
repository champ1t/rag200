#!/usr/bin/env python3
import subprocess
import json
import time

def query_chat(text):
    """Query via CLI and parse JSON response"""
    try:
        proc = subprocess.Popen(
            ['python3', '-m', 'src.main', 'chat', '--json'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd='/Users/jakkapatmac/Documents/NT/RAG/rag_web'
        )
        
        stdout, stderr = proc.communicate(input=text + '\n', timeout=30)
        
        # Parse JSON from last line
        for line in reversed(stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                return json.loads(line)
        
        return {"error": "No JSON found", "route": "error"}
    except Exception as e:
        return {"error": str(e), "route": "error"}

tests = [
    ("TC-D1", "ZTE-SW Command", "article_link_only"),
    ("TC-D2", "zte-sw command", "article_link_only"),
    ("TC-D3", "zte sw command", "article"),
    ("TC-O1", "ONU Command", "article"),
    ("TC-L1", "show power DE", "article"),
    ("TC-G1", "Cisco OLT new command 2024", "blocked|miss"),
]

print("=" * 60)
print("PHASE 20+ TEST RESULTS")
print("=" * 60)

passed = 0
total = len(tests)

for test_id, query, expected_route in tests:
    print(f"\n{test_id}: {query}")
    res = query_chat(query)
    route = res.get('route', 'error')
    
    # Check if route matches expected pattern
    match = any(exp in route for exp in expected_route.split('|'))
    status = "✅" if match else "❌"
    
    print(f"  Route: {route}")
    print(f"  Status: {status}")
    
    if match:
        passed += 1

print("\n" + "=" * 60)
print(f"SUMMARY: {passed}/{total} tests passed ({passed*100//total}%)")
print("=" * 60)
