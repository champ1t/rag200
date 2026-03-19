"""
User Feedback Handler

Collects user feedback (like/dislike + comments) to improve answer quality.

Features:
- Save feedback to JSONL log
- Track satisfaction ratings (like/dislike)
- Collect detailed comments
- Generate feedback statistics
"""

import json
import time
import os
from typing import Dict, Any, List, Optional
import hashlib


class FeedbackHandler:
    """
    Handle user feedback collection and storage.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize feedback handler.
        
        Args:
            log_dir: Directory to store feedback logs
        """
        self.log_dir = log_dir
        self.feedback_file = os.path.join(log_dir, "user_feedback.jsonl")
        
        # Create logs directory if not exists
        os.makedirs(log_dir, exist_ok=True)
    
    def save_feedback(
        self,
        session_id: str,
        query_id: str,
        query: str,
        answer_preview: str,
        rating: str,
        comment: Optional[str] = None,
        route: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save user feedback to log file.
        
        Args:
            session_id: User session identifier
            query_id: Unique query identifier
            query: Original user query
            answer_preview: Preview of answer (first 200 chars)
            rating: "like" or "dislike"
            comment: Optional user comment
            route: Route taken to answer query
            metadata: Additional metadata
        
        Returns:
            True if saved successfully
        """
        # Validate rating
        if rating not in ["like", "dislike"]:
            print(f"[FEEDBACK] Invalid rating: {rating}")
            return False
        
        # Create feedback entry
        feedback_entry = {
            "timestamp": time.time(),
            "session_id": session_id,
            "query_id": query_id,
            "query": query,
            "answer_preview": answer_preview[:200] if answer_preview else "",
            "rating": rating,
            "comment": comment or "",
            "route": route or "unknown",
            "metadata": metadata or {}
        }
        
        try:
            # Append to JSONL file
            with open(self.feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")
            
            print(f"[FEEDBACK] Saved {rating} feedback for query_id: {query_id}")
            return True
        except Exception as e:
            print(f"[FEEDBACK] Error saving feedback: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get aggregate feedback statistics.
        
        Returns:
            Dict with stats: total, likes, dislikes, like_rate, etc.
        """
        if not os.path.exists(self.feedback_file):
            return {
                "total": 0,
                "likes": 0,
                "dislikes": 0,
                "like_rate": 0.0,
                "with_comments": 0
            }
        
        total = 0
        likes = 0
        dislikes = 0
        with_comments = 0
        
        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        total += 1
                        
                        if entry.get("rating") == "like":
                            likes += 1
                        elif entry.get("rating") == "dislike":
                            dislikes += 1
                        
                        if entry.get("comment"):
                            with_comments += 1
                    except:
                        continue
            
            like_rate = (likes / total * 100) if total > 0 else 0.0
            
            return {
                "total": total,
                "likes": likes,
                "dislikes": dislikes,
                "like_rate": round(like_rate, 1),
                "with_comments": with_comments
            }
        except Exception as e:
            print(f"[FEEDBACK] Error reading stats: {e}")
            return {
                "total": 0,
                "likes": 0,
                "dislikes": 0,
                "like_rate": 0.0,
                "with_comments": 0
            }
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent feedback entries.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of recent feedback entries
        """
        if not os.path.exists(self.feedback_file):
            return []
        
        entries = []
        
        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except:
                        continue
            
            # Return last N entries
            return entries[-limit:] if len(entries) > limit else entries
        except Exception as e:
            print(f"[FEEDBACK] Error reading recent feedback: {e}")
            return []
    
    def get_negative_feedback(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent negative (dislike) feedback for analysis.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of dislike feedback entries
        """
        if not os.path.exists(self.feedback_file):
            return []
        
        dislikes = []
        
        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("rating") == "dislike":
                            dislikes.append(entry)
                    except:
                        continue
            
            # Return last N dislikes
            return dislikes[-limit:] if len(dislikes) > limit else dislikes
        except Exception as e:
            print(f"[FEEDBACK] Error reading negative feedback: {e}")
            return []
    
    @staticmethod
    def generate_query_id(query: str, session_id: str, timestamp: float) -> str:
        """
        Generate unique query ID for tracking.
        
        Args:
            query: User query
            session_id: Session identifier
            timestamp: Query timestamp
        
        Returns:
            Unique query ID (hash)
        """
        # Create hash from query + session + timestamp
        data = f"{query}:{session_id}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


# Test module
if __name__ == "__main__":
    print("=" * 60)
    print("FeedbackHandler Test")
    print("=" * 60)
    
    handler = FeedbackHandler(log_dir="logs_test")
    
    # Test 1: Save like feedback
    print("\n[Test 1: Save Like Feedback]")
    query_id = FeedbackHandler.generate_query_id("ศูนย์หาดใหญ่", "test-001", time.time())
    success = handler.save_feedback(
        session_id="test-001",
        query_id=query_id,
        query="ศูนย์หาดใหญ่โทรอะไร",
        answer_preview="เบอร์ติดต่อศูนย์หาดใหญ่: 074-xxx-xxxx",
        rating="like",
        comment="ตอบถูกต้อง รวดเร็ว",
        route="contact"
    )
    assert success, "Failed to save like feedback"
    print("✅ Like feedback saved")
    
    # Test 2: Save dislike feedback
    print("\n[Test 2: Save Dislike Feedback]")
    query_id2 = FeedbackHandler.generate_query_id("แก้ไข OLT", "test-002", time.time())
    success = handler.save_feedback(
        session_id="test-002",
        query_id=query_id2,
        query="แก้ไข OLT ยังไง",
        answer_preview="ขออภัย ไม่พบข้อมูล...",
        rating="dislike",
        comment="ตอบไม่ตรงคำถาม",
        route="article_miss"
    )
    assert success, "Failed to save dislike feedback"
    print("✅ Dislike feedback saved")
    
    # Test 3: Get stats
    print("\n[Test 3: Get Feedback Stats]")
    stats = handler.get_feedback_stats()
    print(f"  Total: {stats['total']}")
    print(f"  Likes: {stats['likes']}")
    print(f"  Dislikes: {stats['dislikes']}")
    print(f"  Like Rate: {stats['like_rate']}%")
    print(f"  With Comments: {stats['with_comments']}")
    assert stats['total'] >= 2, "Stats count incorrect"
    print("✅ Stats calculation works")
    
    # Test 4: Get recent feedback
    print("\n[Test 4: Get Recent Feedback]")
    recent = handler.get_recent_feedback(limit=5)
    print(f"  Recent entries: {len(recent)}")
    for entry in recent:
        print(f"  - [{entry['rating']}] {entry['query'][:30]}...")
    assert len(recent) >= 2, "Recent feedback count incorrect"
    print("✅ Recent feedback retrieval works")
    
    # Test 5: Get negative feedback
    print("\n[Test 5: Get Negative Feedback]")
    negative = handler.get_negative_feedback(limit=10)
    print(f"  Negative entries: {len(negative)}")
    for entry in negative:
        print(f"  - {entry['query'][:30]}... | Comment: {entry['comment']}")
    print("✅ Negative feedback filtering works")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
