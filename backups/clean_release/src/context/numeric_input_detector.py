"""
Numeric Input Detector

Purpose:
Detect pure numeric input BEFORE intent detection to enable
deterministic selection resolution.

Design:
- Ultra-lightweight (regex only)
- Zero false positives (strict digit-only matching)
- Returns integer or None

Usage:
    detector = NumericInputDetector()
    
    result = detector.is_numeric_selection("1")    # Returns 1
    result = detector.is_numeric_selection("10")   # Returns 10
    result = detector.is_numeric_selection("abc")  # Returns None
    result = detector.is_numeric_selection("1 abc") # Returns None
"""


class NumericInputDetector:
    """
    Detect pure numeric input for selection resolution.
    
    Rules:
    - Query must be digits only (after strip)
    - No spaces, letters, or special characters
    - Valid range: 1-999 (reasonable selection limit)
    """
    
    def __init__(self, max_number: int = 999):
        """
        Initialize detector.
        
        Args:
            max_number: Maximum valid number (default 999)
        """
        self.max_number = max_number
    
    def is_numeric_selection(self, query: str) -> int | None:
        """
        Check if query is pure numeric selection.
        
        Args:
            query: User input query
        
        Returns:
            Integer if valid numeric selection, None otherwise
        
        Examples:
            >>> detector = NumericInputDetector()
            >>> detector.is_numeric_selection("1")
            1
            >>> detector.is_numeric_selection("10")
            10
            >>> detector.is_numeric_selection("abc")
            None
            >>> detector.is_numeric_selection("1 abc")
            None
            >>> detector.is_numeric_selection("  5  ")
            5
        """
        if not query:
            return None
        
        # Strip whitespace
        q_stripped = query.strip()
        
        # Check if all characters are digits
        if not q_stripped.isdigit():
            return None
        
        # Convert to integer
        number = int(q_stripped)
        
        # Validate range (must be positive and <= max_number)
        if number < 1 or number > self.max_number:
            return None
        
        return number
    
    def validate_in_range(self, number: int, max_valid: int) -> bool:
        """
        Validate if number is in valid range for selection.
        
        Args:
            number: Selected number
            max_valid: Maximum valid number from session
        
        Returns:
            True if in range, False otherwise
        """
        return 1 <= number <= max_valid


# Test module
if __name__ == "__main__":
    detector = NumericInputDetector()
    
    print("=" * 60)
    print("NumericInputDetector Test")
    print("=" * 60)
    
    test_cases = [
        ("1", 1),
        ("10", 10),
        ("999", 999),
        ("  5  ", 5),
        ("abc", None),
        ("1 abc", None),
        ("1.5", None),
        ("0", None),  # Invalid (< 1)
        ("1000", None),  # Invalid (> 999)
        ("", None),
        ("   ", None),
    ]
    
    print("\nTest Cases:")
    for query, expected in test_cases:
        result = detector.is_numeric_selection(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query}' → {result} (expected: {expected})")
    
    print("\n" + "=" * 60)
    print("Range Validation:")
    print(f"  is_numeric_selection('3') in range 1-5: {detector.validate_in_range(3, 5)}")
    print(f"  is_numeric_selection('10') in range 1-5: {detector.validate_in_range(10, 5)}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed")
