"""
Feedback System Integration Test

Tests feedback collection end-to-end:
1. Submit like/dislike feedback via API
2. Retrieve feedback stats
3. Verify storage in JSONL
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
        print("✅ API is healthy")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ API server not running. Please start with: uvicorn src.api_server:app --reload")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_submit_like_feedback():
    """Test 2: Submit like feedback"""
    print("\n" + "=" * 60)
    print("Test 2: Submit Like Feedback")
    print("=" * 60)
    
    feedback_data = {
        "query_id": f"test-{int(time.time())}-001",
        "session_id": "test-session",
        "query": "ศูนย์หาดใหญ่โทรอะไร",
        "answer": "เบอร์ติดต่อศูนย์หาดใหญ่: 074-xxx-xxxx",
        "rating": "like",
        "comment": "ตอบถูกต้อง รวดเร็ว",
        "route": "contact"
    }
    
    response = requests.post(f"{API_BASE}/feedback", json=feedback_data, timeout=5)
    assert response.status_code == 200, f"Submit failed: {response.status_code}"
    
    data = response.json()
    assert data["success"] == True, "Feedback not saved"
    
    print(f"  ✅ Like feedback submitted")
    print(f"  Message: {data['message']}")
    return True


def test_submit_dislike_feedback():
    """Test 3: Submit dislike feedback"""
    print("\n" + "=" * 60)
    print("Test 3: Submit Dislike Feedback")
    print("=" * 60)
    
    feedback_data = {
        "query_id": f"test-{int(time.time())}-002",
        "session_id": "test-session",
        "query": "แก้ไข OLT ยังไง",
        "answer": "ขออภัย ไม่พบข้อมูล",
        "rating": "dislike",
        "comment": "ตอบไม่ตรงคำถาม ควรให้ขั้นตอนแก้ไข",
        "route": "article_miss"
    }
    
    response = requests.post(f"{API_BASE}/feedback", json=feedback_data, timeout=5)
    assert response.status_code == 200, f"Submit failed: {response.status_code}"
    
    data = response.json()
    assert data["success"] == True, "Feedback not saved"
    
    print(f"  ✅ Dislike feedback submitted")
    print(f"  Message: {data['message']}")
    return True


def test_get_feedback_stats():
    """Test 4: Get feedback statistics"""
    print("\n" + "=" * 60)
    print("Test 4: Get Feedback Stats")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/feedback/stats", timeout=5)
    assert response.status_code == 200, f"Stats request failed: {response.status_code}"
    
    stats = response.json()
    print(f"  Total Feedback: {stats['total']}")
    print(f"  Likes: {stats['likes']}")
    print(f"  Dislikes: {stats['dislikes']}")
    print(f"  Like Rate: {stats['like_rate']}%")
    print(f"  With Comments: {stats['with_comments']}")
    
    assert stats['total'] >= 2, "Stats count incorrect"
    assert stats['likes'] >= 1, "No likes recorded"
    assert stats['dislikes'] >= 1, "No dislikes recorded"
    
    print("✅ Feedback stats working correctly")
    return True


def test_feedback_storage():
    """Test 5: Verify feedback stored in file"""
    print("\n" + "=" * 60)
    print("Test 5: Verify Feedback Storage")
    print("=" * 60)
    
    feedback_file = "logs/user_feedback.jsonl"
    
    assert os.path.exists(feedback_file), "Feedback file not created"
    print(f"  ✅ Feedback file exists: {feedback_file}")
    
    # Read last 2 entries
    with open(feedback_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    assert len(lines) >= 2, "Not enough feedback entries"
    print(f"  Total entries in file: {len(lines)}")
    
    # Check last entry
    last_entry = json.loads(lines[-1])
    print(f"  Last entry:")
    print(f"    - Rating: {last_entry['rating']}")
    print(f"    - Query: {last_entry['query']}")
    print(f"    - Comment: {last_entry['comment'][:50]}...")
    
    print("✅ Feedback storage verified")
    return True


def test_feedback_demo_page():
    """Test 6: Feedback demo page accessible"""
    print("\n" + "=" * 60)
    print("Test 6: Feedback Demo Page")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/feedback-demo", timeout=5)
    assert response.status_code == 200, f"Demo page failed: {response.status_code}"
    
    html = response.text
    assert 'ให้ Feedback' in html, "Demo page content missing"
    assert 'feedback.js' in html, "JavaScript reference missing"
    
    print("✅ Feedback demo page accessible")
    print(f"  Open in browser: {API_BASE}/feedback-demo")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("FEEDBACK SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Health check first
    if not test_api_health():
        print("\n" + "=" * 60)
        print("❌ API server not running. Start with:")
        print("   uvicorn src.api_server:app --reload")
        print("=" * 60)
        sys.exit(1)
    
    # Continue with other tests
    try:
        test_submit_like_feedback()
        test_submit_dislike_feedback()
        test_get_feedback_stats()
        test_feedback_storage()
        test_feedback_demo_page()
        
        print("\n" + "=" * 60)
        print("✅ ALL FEEDBACK TESTS PASSED!")
        print("=" * 60)
        print("\n📱 Feedback Demo: http://localhost:8000/feedback-demo")
        print("📊 Feedback Stats: http://localhost:8000/feedback/stats")
        print("📝 Feedback Log: logs/user_feedback.jsonl")
        print("\nNext Steps:")
        print("1. Open demo page and try submitting feedback")
        print("2. Check stats to see aggregated data")
        print("3. Review feedback log file for details")
        
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
