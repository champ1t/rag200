"""
Test Context Persistence - Verify session-based context memory

Tests:
1. Context saves to file when session_id is provided
2. Context loads from file on next query in same session
3. Context expires after timeout
4. Different sessions have isolated contexts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.context.session_store import SessionStore
from src.context import context_manager
import time

def test_session_store_basic():
    """Test 1: Basic save and load"""
    print("\n" + "=" * 60)
    print("Test 1: Basic Save and Load")
    print("=" * 60)
    
    store = SessionStore(sessions_dir="data/sessions_test")
    
    # Create context
    context = context_manager.create_context(
        query="ศูนย์หาดใหญ่โทรอะไร",
        intent="CONTACT_LOOKUP",
        route="contact",
        entities={"หาดใหญ่": "LOCATION"},
        result_summary="Found contact for หาดใหญ่"
    )
    
    # Save
    session_id = "test-user-001"
    success = store.save_context(session_id, context)
    assert success, "Failed to save context"
    print(f"✅ Saved context for session {session_id}")
    
    # Load
    loaded = store.load_context(session_id)
    assert loaded is not None, "Failed to load context"
    assert loaded["query"] == "ศูนย์หาดใหญ่โทรอะไร"
    assert loaded["entities"]["หาดใหญ่"] == "LOCATION"
    print(f"✅ Loaded context: query='{loaded['query']}', entities={loaded['entities']}")
    
    # Cleanup
    store.delete_context(session_id)
    print("✅ Test 1 passed")


def test_context_manager_helpers():
    """Test 2: Context manager save/load helpers"""
    print("\n" + "=" * 60)
    print("Test 2: Context Manager Helpers")
    print("=" * 60)
    
    session_id = "test-user-002"
    
    # Create and save
    context = context_manager.create_context(
        query="ขอเบอร์",
        intent="CONTACT_LOOKUP",
        route="contact",
        entities={"RNOC": "ORGANIZATION"},
    )
    
    success = context_manager.save_session_context(session_id, context)
    assert success, "Failed to save via helper"
    print(f"✅ Saved via helper for session {session_id}")
    
    # Load via helper
    loaded = context_manager.load_session_context(session_id)
    assert loaded is not None, "Failed to load via helper"
    assert loaded["query"] == "ขอเบอร์"
    print(f"✅ Loaded via helper: query='{loaded['query']}'")
    
    # Cleanup
    store = SessionStore()
    store.delete_context(session_id)
    print("✅ Test 2 passed")


def test_context_expiry():
    """Test 3: Context expiry"""
    print("\n" + "=" * 60)
    print("Test 3: Context Expiry")
    print("=" * 60)
    
    store = SessionStore(sessions_dir="data/sessions_test")
    
    # Create old context (simulate)
    session_id = "test-user-003"
    old_context = context_manager.create_context(
        query="old query",
        intent="CONTACT_LOOKUP",
        route="contact"
    )
    
    # Manually create expired file
    import json
    session_path = store._get_session_path(session_id)
    save_data = {
        "session_id": session_id,
        "context": old_context,
        "saved_at": time.time() - 400  # 400 seconds ago (> 300s expiry)
    }
    with open(session_path, 'w') as f:
        json.dump(save_data, f)
    
    # Try to load
    loaded = store.load_context(session_id)
    assert loaded is None, "Expired context should return None"
    print("✅ Expired context correctly returned None")
    print("✅ Test 3 passed")


def test_session_isolation():
    """Test 4: Different sessions have isolated contexts"""
    print("\n" + "=" * 60)
    print("Test 4: Session Isolation")
    print("=" * 60)
    
    # Session 1
    context1 = context_manager.create_context(
        query="ศูนย์หาดใหญ่",
        intent="CONTACT_LOOKUP",
        route="contact",
        entities={"หาดใหญ่": "LOCATION"}
    )
    context_manager.save_session_context("user-A", context1)
    
    # Session 2
    context2 = context_manager.create_context(
        query="ศูนย์ภูเก็ต",
        intent="CONTACT_LOOKUP",
        route="contact",
        entities={"ภูเก็ต": "LOCATION"}
    )
    context_manager.save_session_context("user-B", context2)
    
    # Load and verify isolation
    loaded_A = context_manager.load_session_context("user-A")
    loaded_B = context_manager.load_session_context("user-B")
    
    assert loaded_A["query"] == "ศูนย์หาดใหญ่", "Session A context incorrect"
    assert loaded_B["query"] == "ศูนย์ภูเก็ต", "Session B context incorrect"
    assert loaded_A["entities"] != loaded_B["entities"], "Sessions not isolated"
    
    print(f"✅ Session A: {loaded_A['query']}")
    print(f"✅ Session B: {loaded_B['query']}")
    print("✅ Sessions correctly isolated")
    
    # Cleanup
    store = SessionStore()
    store.delete_context("user-A")
    store.delete_context("user-B")
    print("✅ Test 4 passed")


if __name__ == "__main__":
    try:
        test_session_store_basic()
        test_context_manager_helpers()
        test_context_expiry()
        test_session_isolation()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
