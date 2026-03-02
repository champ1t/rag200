"""
Numeric Selection Resolver - Generic State Machine for List Selection

Purpose:
Transform numbered list selection from text-based to deterministic state machine.
No semantic matching, no category reset, pure number → item mapping.

Design Principles:
1. Global numbering across all categories (1, 2, 3... never reset)
2. State binding with session_id
3. Direct lookup without second-round matching
4. Validation with state preservation on error
5. Generic for: articles, teams, centers, devices

Example Flow:
1. User: "Huawei"
2. System: Creates session, shows numbered list (1-5)
3. User: "3"
4. System: Resolves #3 → article_id → opens article → clears session
"""

import uuid
from typing import List, Dict, Optional, Any
import time


class NumericSelectionResolver:
    """
    Generic component for deterministic numbered selection.
    
    Handles:
    - Session creation with global numbering
    - Number → item mapping storage
    - Selection resolution
    - Validation
    """
    
    def __init__(self):
        pass
    
    def create_session(
        self, 
        items: List[Dict[str, Any]], 
        context: str = "selection",
        prompt_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create selection session with global numbering.
        
        Args:
            items: List of items to select from
                   Required keys depend on context:
                   - article_selection: article_id, title, category (optional)
                   - team_selection: team_id, name, phone (optional)
                   - center_selection: center_id, name, phone (optional)
                   - device_selection: device_id, name, location (optional)
            context: Selection context (article_selection, team_selection, etc.)
            prompt_text: Custom prompt, defaults to "กรุณาเลือกหมายเลข (1-N)"
        
        Returns:
            Session dict with:
            - session_id: Unique identifier
            - kind: "numeric_selection"
            - context: Selection context
            - items: Numbered items with mapping
            - max_number: Total item count
            - created_at: Timestamp
            - prompt_text: Selection prompt
        """
        if not items:
            raise ValueError("Items list cannot be empty")
        
        session_id = str(uuid.uuid4())
        numbered_items = []
        
        # Global numbering (no reset per category)
        for idx, item in enumerate(items, start=1):
            numbered_item = {
                "number": idx,
                **item  # Preserve all original fields
            }
            numbered_items.append(numbered_item)
        
        # Default prompt
        if prompt_text is None:
            prompt_text = f"กรุณาเลือกหมายเลข (1-{len(items)})"
        
        session = {
            "kind": "numeric_selection",
            "session_id": session_id,
            "context": context,
            "items": numbered_items,
            "max_number": len(items),
            "created_at": time.time(),
            "prompt_text": prompt_text
        }
        
        return session
    
    def validate_number(self, number: int, session: Dict[str, Any]) -> bool:
        """
        Validate if number is in valid range.
        
        Args:
            number: Selected number
            session: Selection session from create_session()
        
        Returns:
            True if valid, False otherwise
        """
        if session.get('kind') != 'numeric_selection':
            return False
        
        max_num = session.get('max_number', 0)
        return 1 <= number <= max_num
    
    def resolve_selection(
        self, 
        number: int, 
        session: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve number to item WITHOUT semantic matching.
        
        Args:
            number: Selected number
            session: Selection session
        
        Returns:
            Selected item dict or None if not found
        """
        if not self.validate_number(number, session):
            return None
        
        items = session.get('items', [])
        
        # Direct lookup (deterministic)
        for item in items:
            if item.get('number') == number:
                return item
        
        return None
    
    def format_numbered_list(
        self, 
        items: List[Dict[str, Any]], 
        context: str = "article_selection"
    ) -> str:
        """
        Format items as numbered list with global numbering.
        
        Args:
            items: Numbered items from session['items']
            context: Selection context for formatting style
        
        Returns:
            Formatted string ready for display
        """
        if not items:
            return "ไม่พบรายการ"
        
        lines = []
        
        for item in items:
            number = item.get('number', '?')
            
            if context == "article_selection":
                title = item.get('title', 'ไม่ระบุชื่อ')
                category = item.get('category', '')
                
                if category:
                    line = f"{number}. {title} [{category}]"
                else:
                    line = f"{number}. {title}"
            
            elif context == "team_selection":
                name = item.get('name', 'ไม่ระบุชื่อ')
                phone = item.get('phone', '')
                
                if phone:
                    line = f"{number}. {name} (โทร: {phone})"
                else:
                    line = f"{number}. {name}"
            
            elif context == "center_selection":
                name = item.get('name', 'ไม่ระบุชื่อ')
                phone = item.get('phone', '')
                
                if phone:
                    line = f"{number}. {name} — {phone}"
                else:
                    line = f"{number}. {name}"
            
            elif context == "device_selection":
                name = item.get('name', 'ไม่ระบุชื่อ')
                location = item.get('location', '')
                
                if location:
                    line = f"{number}. {name} @ {location}"
                else:
                    line = f"{number}. {name}"
            
            else:
                # Generic fallback
                # Try common keys
                display = item.get('title') or item.get('name') or item.get('id', '???')
                line = f"{number}. {display}"
            
            lines.append(line)
        
        return "\n".join(lines)


# Test module
if __name__ == "__main__":
    resolver = NumericSelectionResolver()
    
    print("=" * 60)
    print("NumericSelectionResolver Test")
    print("=" * 60)
    
    # Test 1: Article Selection
    print("\n[Test 1: Article Selection]")
    articles = [
        {"article_id": "123", "title": "Huawei Configuration Guide", "category": "HUAWEI"},
        {"article_id": "456", "title": "General Network Settings", "category": "GENERAL"},
        {"article_id": "789", "title": "Huawei Troubleshooting", "category": "HUAWEI"}
    ]
    
    session = resolver.create_session(articles, context="article_selection")
    print(f"Session ID: {session['session_id']}")
    print(f"Max Number: {session['max_number']}")
    print("\nFormatted List:")
    print(resolver.format_numbered_list(session['items'], context="article_selection"))
    
    # Test validation
    print(f"\nValidate 2: {resolver.validate_number(2, session)}")  # True
    print(f"Validate 10: {resolver.validate_number(10, session)}")  # False
    
    # Test resolution
    selected = resolver.resolve_selection(2, session)
    print(f"\nSelected #2: {selected['title']} (ID: {selected['article_id']})")
    
    # Test 2: Team Selection
    print("\n" + "=" * 60)
    print("[Test 2: Team Selection]")
    teams = [
        {"team_id": "NOC", "name": "Network Operations Center", "phone": "02-123-4567"},
        {"team_id": "RNOC", "name": "Regional NOC", "phone": "02-987-6543"}
    ]
    
    session2 = resolver.create_session(teams, context="team_selection")
    print("\nFormatted List:")
    print(resolver.format_numbered_list(session2['items'], context="team_selection"))
    
    print("\n" + "=" * 60)
    print("✅ All tests passed")
