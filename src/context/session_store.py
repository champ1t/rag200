"""
Session Storage Manager

Handles persistent storage of conversation context across sessions.
Stores context in JSON files: data/sessions/{session_id}.json

Features:
- Save/load session context
- Auto-cleanup of expired sessions
- Thread-safe file operations
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import threading


class SessionStore:
    """
    Persistent storage for conversation context.
    Each session is stored as a separate JSON file.
    """
    
    def __init__(self, sessions_dir: str = "data/sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        
        # Session expiry time (5 minutes, same as context_manager)
        self.expiry_seconds = 300
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        # Sanitize session_id to prevent directory traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.sessions_dir / f"{safe_id}.json"
    
    def save_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """
        Save conversation context for a session.
        
        Args:
            session_id: Unique session identifier
            context: Context dict from context_manager.create_context()
        
        Returns:
            True if saved successfully, False otherwise
        """
        if not session_id or not context:
            return False
        
        try:
            with self._lock:
                session_path = self._get_session_path(session_id)
                
                # Add save timestamp
                save_data = {
                    "session_id": session_id,
                    "context": context,
                    "saved_at": time.time()
                }
                
                with open(session_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            print(f"[SESSION_STORE] Error saving context: {e}")
            return False
    
    def load_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load conversation context for a session.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Context dict or None if not found/expired
        """
        if not session_id:
            return None
        
        try:
            with self._lock:
                session_path = self._get_session_path(session_id)
                
                if not session_path.exists():
                    return None
                
                with open(session_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                
                # Check expiry
                saved_at = save_data.get("saved_at", 0)
                age_seconds = time.time() - saved_at
                
                if age_seconds > self.expiry_seconds:
                    # Context expired, delete file
                    print(f"[SESSION_STORE] Context expired for session {session_id} (age: {age_seconds:.1f}s)")
                    session_path.unlink(missing_ok=True)
                    return None
                
                context = save_data.get("context", {})
                print(f"[SESSION_STORE] Loaded context for session {session_id} (age: {age_seconds:.1f}s)")
                return context
                
        except Exception as e:
            print(f"[SESSION_STORE] Error loading context: {e}")
            return None
    
    def delete_context(self, session_id: str) -> bool:
        """
        Delete conversation context for a session.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if deleted, False otherwise
        """
        if not session_id:
            return False
        
        try:
            with self._lock:
                session_path = self._get_session_path(session_id)
                session_path.unlink(missing_ok=True)
                return True
        except Exception as e:
            print(f"[SESSION_STORE] Error deleting context: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Clean up all expired session files.
        
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        try:
            with self._lock:
                for session_file in self.sessions_dir.glob("*.json"):
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            save_data = json.load(f)
                        
                        saved_at = save_data.get("saved_at", 0)
                        age_seconds = time.time() - saved_at
                        
                        if age_seconds > self.expiry_seconds:
                            session_file.unlink()
                            deleted_count += 1
                    except Exception:
                        # If we can't read the file, delete it
                        session_file.unlink(missing_ok=True)
                        deleted_count += 1
                
                if deleted_count > 0:
                    print(f"[SESSION_STORE] Cleaned up {deleted_count} expired sessions")
                    
        except Exception as e:
            print(f"[SESSION_STORE] Error during cleanup: {e}")
        
        return deleted_count
    
    def list_active_sessions(self) -> list[str]:
        """
        List all active (non-expired) session IDs.
        
        Returns:
            List of session IDs
        """
        active_sessions = []
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    
                    saved_at = save_data.get("saved_at", 0)
                    age_seconds = time.time() - saved_at
                    
                    if age_seconds <= self.expiry_seconds:
                        session_id = save_data.get("session_id", session_file.stem)
                        active_sessions.append(session_id)
                except Exception:
                    pass
        except Exception as e:
            print(f"[SESSION_STORE] Error listing sessions: {e}")
        
        return active_sessions


# Test module
if __name__ == "__main__":
    print("=" * 60)
    print("SessionStore Test")
    print("=" * 60)
    
    store = SessionStore(sessions_dir="data/sessions_test")
    
    # Test 1: Save and load
    print("\n[Test 1: Save and Load]")
    test_context = {
        "type": "contact",
        "query": "ศูนย์หาดใหญ่",
        "entities": {"หาดใหญ่": "LOCATION"},
        "intent": "CONTACT_LOOKUP",
        "timestamp": time.time()
    }
    
    session_id = "test-session-001"
    store.save_context(session_id, test_context)
    print(f"✅ Saved context for {session_id}")
    
    loaded = store.load_context(session_id)
    assert loaded is not None
    assert loaded["type"] == "contact"
    print(f"✅ Loaded context: {loaded['query']}")
    
    # Test 2: Non-existent session
    print("\n[Test 2: Non-existent Session]")
    loaded = store.load_context("non-existent-session")
    assert loaded is None
    print("✅ Returns None for non-existent session")
    
    # Test 3: Delete
    print("\n[Test 3: Delete Session]")
    store.delete_context(session_id)
    loaded = store.load_context(session_id)
    assert loaded is None
    print("✅ Session deleted successfully")
    
    # Test 4: Expiry (simulate old timestamp)
    print("\n[Test 4: Expired Session]")
    old_context = {
        "type": "contact",
        "query": "old query",
        "timestamp": time.time() - 400  # 400 seconds old (> 300s expiry)
    }
    session_id2 = "test-session-002"
    
    # Manually create old file
    session_path = store._get_session_path(session_id2)
    save_data = {
        "session_id": session_id2,
        "context": old_context,
        "saved_at": time.time() - 400
    }
    with open(session_path, 'w') as f:
        json.dump(save_data, f)
    
    loaded = store.load_context(session_id2)
    assert loaded is None
    print("✅ Expired context returns None and is deleted")
    
    # Test 5: Cleanup
    print("\n[Test 5: Cleanup Expired Sessions]")
    # Create multiple sessions
    for i in range(5):
        sid = f"test-session-{i}"
        ctx = {"type": "test", "query": f"query {i}", "timestamp": time.time()}
        store.save_context(sid, ctx)
    
    active = store.list_active_sessions()
    print(f"✅ Created {len(active)} active sessions")
    
    deleted = store.cleanup_expired()
    print(f"✅ Cleanup deleted {deleted} expired sessions")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
