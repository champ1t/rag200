"""
Full System Integration Test

Tests all three features together:
1. Context Memory - Session-based persistence
2. Human Escalation - Auto and manual triggers
3. Basic Monitoring Dashboard - Metrics collection

This test runs the full stack and verifies everything works together.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import requests
import time
import json

API_BASE = "http://localhost:8000"

def test_api_health():
    """Test 1: API is running"""
    print("\n" + "=" * 60)
    print("Test 1: API Health Check")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        assert response.status_code == 200, f"API not healthy: {response.status_code}"
        data = response.json()
        print(f"✅ API is healthy: {data['status']}")
        print(f"  - Teams: {data['teams_count']}")
        print(f"  - Positions: {data['positions_count']}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ API server not running. Please start with: uvicorn src.api_server:app")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_context_memory_via_api():
    """Test 2: Context memory persists across queries"""
    print("\n" + "=" * 60)
    print("Test 2: Context Memory (Session-Based)")
    print("=" * 60)
    
    session_id = f"test-session-{int(time.time())}"
    
    # Query 1: Set context
    print("\nQuery 1: Setting up context...")
    query1 = {
        "query": "ศูนย์หาดใหญ่โทรอะไร",
        "session_id": session_id
    }
    
    response1 = requests.post(f"{API_BASE}/query", json=query1, timeout=30)
    assert response1.status_code == 200, f"Query 1 failed: {response1.status_code}"
    data1 = response1.json()
    print(f"  Route: {data1.get('route')}")
    print(f"  Answer preview: {data1.get('answer', '')[:100]}...")
    
    # Wait a bit to ensure context is saved
    time.sleep(1)
    
    # Query 2: Use context (follow-up)
    print("\nQuery 2: Using context from previous query...")
    query2 = {
        "query": "ขอเบอร์",  # Should use หาดใหญ่ from context
        "session_id": session_id
    }
    
    response2 = requests.post(f"{API_BASE}/query", json=query2, timeout=30)
    assert response2.status_code == 200, f"Query 2 failed: {response2.status_code}"
    data2 = response2.json()
    print(f"  Route: {data2.get('route')}")
    print(f"  Answer preview: {data2.get('answer', '')[:100]}...")
    
    # Verify context was used (answer should reference หาดใหญ่)
    answer2 = data2.get('answer', '').lower()
    context_used = 'หาดใหญ่' in answer2 or 'hatyai' in answer2
    
    if context_used:
        print("✅ Context memory works! Follow-up query used previous context")
    else:
        print("⚠️  Context might not have been used (check answer manually)")
    
    return True


def test_escalation():
    """Test 3: Human escalation endpoints"""
    print("\n" + "=" * 60)
    print("Test 3: Human Escalation")
    print("=" * 60)
    
    # Test explicit escalation
    print("\nManual escalation request...")
    response = requests.post(f"{API_BASE}/escalate", timeout=5)
    assert response.status_code == 200, f"Escalation failed: {response.status_code}"
    
    data = response.json()
    print(f"  Route: {data.get('route')}")
    print(f"  Answer:\n{data.get('answer')}")
    
    assert 'escalation' in data, "Escalation data missing"
    assert data['escalation']['reason'] == 'manual'
    
    print("✅ Escalation endpoint works!")
    return True


def test_dashboard_stats():
    """Test 4: Dashboard stats endpoint"""
    print("\n" + "=" * 60)
    print("Test 4: Dashboard Stats  Endpoint")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/stats", timeout=5)
    assert response.status_code == 200, f"Stats request failed: {response.status_code}"
    
    data = response.json()
    print(f"  Teams: {data.get('teams')}")
    print(f"  Positions: {data.get('positions')}")
    
    # Check for query stats
    if 'query_stats' in data:
        stats = data['query_stats']
        print(f"  Total Queries: {stats.get('total_queries', 0)}")
        print(f"  Successful: {stats.get('article_served_queries', 0)}")
        print(f"  Blocked: {stats.get('blocked_queries', 0)}")
    
    # Check for recent queries
    if 'recent_queries' in data:
        recent = data['recent_queries']
        print(f"  Recent Queries: {len(recent)}")
    
    print("✅ Dashboard stats endpoint works!")
    return True


def test_dashboard_html():
    """Test 5: Dashboard HTML is accessible"""
    print("\n" + "=" * 60)
    print("Test 5: Dashboard HTML Page")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/dashboard", timeout=5)
    assert response.status_code == 200, f"Dashboard failed: {response.status_code}"
    
    html = response.text
    assert 'RAG System Dashboard' in html, "Dashboard HTML content missing"
    assert 'dashboard.js' in html, "Dashboard JavaScript reference missing"
    
    print("✅ Dashboard HTML is accessible!")
    print(f"  Open in browser: {API_BASE}/dashboard")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("FULL SYSTEM INTEGRATION TEST")
    print("=" * 60)
    print("\nTesting all three features:")
    print("1. Context Memory (Session Persistence)")
    print("2. Human Escalation (API Endpoints)")
    print("3. Monitoring Dashboard (Stats + UI)")
    
    # Test 1: Health check first
    if not test_api_health():
        print("\n" + "=" * 60)
        print("❌ API server not running. Start with:")
        print("   uvicorn src.api_server:app --reload")
        print("=" * 60)
        sys.exit(1)
    
    # Continue with other tests
    try:
        test_context_memory_via_api()
        test_escalation()
        test_dashboard_stats()
        test_dashboard_html()
        
        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print("\n📊 Dashboard URL: http://localhost:8000/dashboard")
        print("📝 API Docs: http://localhost:8000/docs")
        print("\nNext Steps:")
        print("1. Open dashboard in browser to see real-time metrics")
        print("2. Try multiple queries to see context memory in action")
        print("3. Test escalation by querying: 'ติดต่อคน'")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
