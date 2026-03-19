"""
Human Escalation Handler

Detects when users need human assistance and provides contact information.

Triggers:
- Explicit escalation request ("ติดต่อคน", "escalate", "help desk")
- Multiple failed queries in a session
- System errors or critical failures

Features:
- Configurable contact information
- Escalation event logging
- Auto-trigger after N failures
"""

import time
from typing import Dict, Any, Optional


class EscalationHandler:
    """
    Handle escalation to human support.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize escalation handler with config.
        
        Args:
            config: Escalation configuration from config.yaml
        """
        self.config = config.get("escalation", {})
        self.contact_phone = self.config.get("contact_phone", "02-XXX-XXXX")
        self.contact_email = self.config.get("contact_email", "support@example.com")
        self.auto_trigger_threshold = self.config.get("auto_trigger_after_failures", 3)
        
        # Track failure count per session
        self._failure_counts: Dict[str, int] = {}
        self._last_reset: Dict[str, float] = {}
        
        # Session timeout (reset failure count after 10 minutes)
        self.session_timeout = 600  # 10 minutes
    
    def is_escalation_request(self, query: str) -> bool:
        """
        Check if query is an explicit escalation request.
        
        Args:
            query: User query
        
        Returns:
            True if user is requesting human help
        """
        q_lower = query.lower().strip()
        
        escalation_keywords = [
            # Thai
            "ติดต่อคน", "ติดต่อเจ้าหน้าที่", "พูดคุยกับคน",
            "ขอคุยกับคน", "ต้องการคุยกับคน",
            "help desk", "support", "escalate",
            "ติดต่อ support", "ช่วยเหลือ",
            
            # English
            "talk to human", "speak to agent", "contact support",
            "need help", "get help"
        ]
        
        return any(kw in q_lower for kw in escalation_keywords)
    
    def record_failure(self, session_id: str) -> bool:
        """
        Record a query failure for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if auto-escalation threshold reached
        """
        # Reset if session timeout
        last_reset = self._last_reset.get(session_id, 0)
        if time.time() - last_reset > self.session_timeout:
            self._failure_counts[session_id] = 0
            self._last_reset[session_id] = time.time()
        
        # Increment failure count
        self._failure_counts[session_id] = self._failure_counts.get(session_id, 0) + 1
        count = self._failure_counts[session_id]
        
        print(f"[ESCALATION] Session {session_id} failure count: {count}/{self.auto_trigger_threshold}")
        
        # Check threshold
        return count >= self.auto_trigger_threshold
    
    def reset_failures(self, session_id: str):
        """Reset failure count for a session."""
        self._failure_counts[session_id] = 0
        self._last_reset[session_id] = time.time()
    
    def get_escalation_response(
        self, 
        reason: str = "manual",
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate escalation response with contact information.
        
        Args:
            reason: Reason for escalation (manual, auto_threshold, system_error)
            query: Original user query
        
        Returns:
            Response dict with contact info
        """
        # Build message based on reason
        if reason == "manual":
            header = "📞 **ติดต่อเจ้าหน้าที่**\n\n"
            message = "ยินดีให้ความช่วยเหลือครับ คุณสามารถติดต่อทีมสนับสนุนได้ที่:\n\n"
        elif reason == "auto_threshold":
            header = "📞 **ต้องการความช่วยเหลือเพิ่มเติมใช่ไหมครับ?**\n\n"
            message = "ดูเหมือนว่าคุณอาจต้องการความช่วยเหลือเพิ่มเติม คุณสามารถติดต่อทีมสนับสนุนได้ที่:\n\n"
        elif reason == "system_error":
            header = "⚠️ **เกิดข้อผิดพลาดในระบบ**\n\n"
            message = "ขออภัยในความไม่สะดวก กรุณาติดต่อทีมสนับสนุนเพื่อรับความช่วยเหลือ:\n\n"
        else:
            header = "📞 **ติดต่อทีมสนับสนุน**\n\n"
            message = "คุณสามารถติดต่อทีมสนับสนุนได้ที่:\n\n"
        
        # Add contact information
        contact_info = ""
        if self.contact_phone and self.contact_phone != "02-XXX-XXXX":
            contact_info += f"📱 โทร: {self.contact_phone}\n"
        if self.contact_email and self.contact_email != "support@example.com":
            contact_info += f"📧 อีเมล: {self.contact_email}\n"
        
        # Default message if no contact info configured
        if not contact_info:
            contact_info = "📱 โทร: 02-XXX-XXXX (กรุณาตั้งค่าข้อมูลติดต่อใน config.yaml)\n"
        
        answer = header + message + contact_info
        
        # Log escalation event
        self._log_escalation(reason, query)
        
        return {
            "answer": answer,
            "route": f"escalation_{reason}",
            "escalation": {
                "reason": reason,
                "contact_phone": self.contact_phone,
                "contact_email": self.contact_email
            }
        }
    
    def _log_escalation(self, reason: str, query: Optional[str] = None):
        """Log escalation event for metrics."""
        try:
            from src.utils.metrics import MetricsTracker
            metrics = MetricsTracker()
            
            # Log as special metric
            import json
            import os
            log_file = os.path.join(metrics.log_dir, "escalation_events.jsonl")
            
            event = {
                "timestamp": time.time(),
                "reason": reason,
                "query": query
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
            
            print(f"[ESCALATION] Event logged: reason={reason}")
        except Exception as e:
            print(f"[ESCALATION] Failed to log event: {e}")


# Test module
if __name__ == "__main__":
    print("=" * 60)
    print("EscalationHandler Test")
    print("=" * 60)
    
    config = {
        "escalation": {
            "contact_phone": "02-123-4567",
            "contact_email": "support@example.com",
            "auto_trigger_after_failures": 3
        }
    }
    
    handler = EscalationHandler(config)
    
    # Test 1: Explicit request detection
    print("\n[Test 1: Explicit Request Detection]")
    assert handler.is_escalation_request("ติดต่อคน")
    assert handler.is_escalation_request("HELP DESK")
    assert not handler.is_escalation_request("ขอเบอร์ NT")
    print("✅ Explicit request detection works")
    
    # Test 2: Manual escalation response
    print("\n[Test 2: Manual Escalation Response]")
    response = handler.get_escalation_response(reason="manual", query="ติดต่อคน")
    assert "02-123-4567" in response["answer"]
    assert response["route"] == "escalation_manual"
    print(f"✅ Manual escalation response:\n{response['answer']}")
    
    # Test 3: Auto-trigger threshold
    print("\n[Test 3: Auto-Trigger Threshold]")
    session_id = "test-session"
    assert not handler.record_failure(session_id)  # 1st failure
    assert not handler.record_failure(session_id)  # 2nd failure
    assert handler.record_failure(session_id)      # 3rd failure - triggers!
    print("✅ Auto-trigger threshold works (3 failures)")
    
    # Test 4: Response with auto-trigger
    print("\n[Test 4: Auto-Trigger Response]")
    response = handler.get_escalation_response(reason="auto_threshold")
    assert "ต้องการความช่วยเหลือเพิ่มเติม" in response["answer"]
    print(f"✅ Auto-trigger response:\n{response['answer']}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
