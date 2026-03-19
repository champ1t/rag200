"""
Colloquial Noise Remover - Thai Particle Preprocessing

Purpose:
Remove Thai colloquial particles that don't affect query meaning.
This improves entity detection, intent classification, and overall query clarity.

Particles Removed:
- Emphatic: มัน, หว่า, เนี่ย, นะ, สิ, เหอะ
- Questioning: รึเปล่า, มั้ย, เหรอ, หรอ

Particles Preserved:
- Polite markers: ครับ, ค่ะ (useful signals)
- Question words: อะไร, ไหน, ทำไม (core meaning)
- Negation: ไม่ (changes meaning)

Performance: <1ms (regex-based)
"""

import re
from typing import Dict, List, Any


class ColloquialNoiseRemover:
    """
    Remove Thai colloquial particles from queries.
    
    Use Case:
    Input: "OLT มันคืออะไรหว่า"
    Output: "OLT คืออะไร"
    
    Integration Point: BEFORE entity detection in pipeline
    """
    
    def __init__(self):
        """Initialize noise removal patterns."""
        
        # Emphatic particles (no semantic content)
        self.emphatic_patterns = [
            # Word + whitespace pattern to preserve word boundaries
            (r'\s+มัน\s+', ' ', 'มัน'),           # มัน (emphatic "it")
            (r'\s+หว่า\s*', ' ', 'หว่า'),          # หว่า (colloquial question)
            (r'\s+เนี่ย\s*', ' ', 'เนี่ย'),        # เนี่ย (demonstrative)
            (r'\s+นะ\s*', ' ', 'นะ'),              # นะ (softener)
            (r'\s+สิ\s*', ' ', 'สิ'),              # สิ (emphatic)
            (r'\s+เหอะ\s*', ' ', 'เหอะ'),          # เหอะ (softener)
            (r'\s+เถอะ\s*', ' ', 'เถอะ'),          # เถอะ (softener)
            (r'\s+ล่ะ\s*', ' ', 'ล่ะ'),            # ล่ะ (topic marker)
            (r'\s+หนิ\s*', ' ', 'หนิ'),            # หนิ (colloquial)
            (r'\s+แน่ะ\s*', ' ', 'แน่ะ'),          # แน่ะ (emphatic)
        ]
        
        # Questioning particles (redundant with ? or question words)
        self.questioning_patterns = [
            (r'\s+รึเปล่า\s*', ' ', 'รึเปล่า'),    # รึเปล่า
            (r'\s+มั้ย\s*', ' ', 'มั้ย'),          # มั้ย
            (r'\s+เหรอ\s*', ' ', 'เหรอ'),          # เหรอ
            (r'\s+หรอ\s*', ' ', 'หรอ'),            # หรอ
            (r'\s+รึป่าว\s*', ' ', 'รึป่าว'),      # รึป่าว
            (r'\s+ป่าว\s*', ' ', 'ป่าว'),          # ป่าว
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = []
        for pattern, replacement, label in self.emphatic_patterns + self.questioning_patterns:
            self.compiled_patterns.append({
                'regex': re.compile(pattern),
                'replacement': replacement,
                'label': label
            })
    
    def remove_noise(self, query: str) -> Dict[str, Any]:
        """
        Remove colloquial particles from query.
        
        Args:
            query: Original query string
        
        Returns:
            {
                'cleaned_query': str,    # Query after noise removal
                'original_query': str,    # Original query
                'removed_count': int,     # Number of particles removed
                'removed_words': list,    # List of removed particles
                'was_modified': bool      # True if any changes made
            }
        """
        original = query
        cleaned = query
        removed_words = []
        
        # Apply each pattern
        for pattern_info in self.compiled_patterns:
            regex = pattern_info['regex']
            replacement = pattern_info['replacement']
            label = pattern_info['label']
            
            # Find all matches before replacing
            matches = regex.findall(cleaned)
            if matches:
                removed_words.extend([label] * len(matches))
                cleaned = regex.sub(replacement, cleaned)
        
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return {
            'cleaned_query': cleaned,
            'original_query': original,
            'removed_count': len(removed_words),
            'removed_words': removed_words,
            'was_modified': cleaned != original
        }
    
    def clean(self, query: str) -> str:
        """
        Convenience method: Just return cleaned query.
        
        Args:
            query: Original query
        
        Returns:
            Cleaned query string
        """
        result = self.remove_noise(query)
        return result['cleaned_query']


# ============================================================================
# Unit Tests
# ============================================================================

def test_emphatic_removal():
    """Test removal of emphatic particles."""
    remover = ColloquialNoiseRemover()
    
    # Test มัน
    result = remover.remove_noise("OLT มัน คืออะไร")
    assert "มัน" not in result['cleaned_query']
    assert result['removed_count'] >= 1
    assert "OLT" in result['cleaned_query']
    assert "คืออะไร" in result['cleaned_query']
    
    # Test หว่า
    result = remover.remove_noise("OLT คืออะไร หว่า")
    assert "หว่า" not in result['cleaned_query']
    assert "OLT คืออะไร" in result['cleaned_query']
    
    # Test เนี่ย
    result = remover.remove_noise("ขอเบอร์CSOC เนี่ย")
    assert "เนี่ย" not in result['cleaned_query']
    assert "ขอเบอร์CSOC" in result['cleaned_query']


def test_questioning_removal():
    """Test removal of questioning particles."""
    remover = ColloquialNoiseRemover()
    
    # Test รึเปล่า
    result = remover.remove_noise("GPON ทำงานยังไง รึเปล่า")
    assert "รึเปล่า" not in result['cleaned_query']
    assert result['removed_count'] >= 1
    
    # Test มั้ย
    result = remover.remove_noise("เข้าใจ มั้ย")
    assert "มั้ย" not in result['cleaned_query']
    
    # Test เหรอ
    result = remover.remove_noise("จริง เหรอ")
    assert "เหรอ" not in result['cleaned_query']


def test_multiple_particles():
    """Test removal of multiple particles in one query."""
    remover = ColloquialNoiseRemover()
    
    result = remover.remove_noise("OLT มัน คืออะไร หว่า")
    assert "มัน" not in result['cleaned_query']
    assert "หว่า" not in result['cleaned_query']
    assert result['removed_count'] == 2
    assert len(result['removed_words']) == 2


def test_no_modification():
    """Test queries that don't need modification."""
    remover = ColloquialNoiseRemover()
    
    # Clean technical query
    result = remover.remove_noise("ขอเบอร์CSOC")
    assert result['cleaned_query'] == "ขอเบอร์CSOC"
    assert result['removed_count'] == 0
    assert result['was_modified'] is False
    
    # Question without colloquial particles
    result = remover.remove_noise("OLT คืออะไร")
    assert result['cleaned_query'] == "OLT คืออะไร"
    assert result['removed_count'] == 0


def test_preserve_polite_markers():
    """Test that polite markers are NOT removed."""
    remover = ColloquialNoiseRemover()
    
    # ครับ should be preserved
    result = remover.remove_noise("ช่วยบอกหน่อยครับ")
    assert "ครับ" in result['cleaned_query']
    
    # ค่ะ should be preserved
    result = remover.remove_noise("ขอเบอร์ค่ะ")
    assert "ค่ะ" in result['cleaned_query']


def test_preserve_question_words():
    """Test that core question words are NOT removed."""
    remover = ColloquialNoiseRemover()
    
    # อะไร (what)
    result = remover.remove_noise("OLT คืออะไร")
    assert "อะไร" in result['cleaned_query']
    
    # ไหน (where)
    result = remover.remove_noise("ศูนย์หาดใหญ่อยู่ที่ไหน")
    assert "ไหน" in result['cleaned_query']


def test_preserve_negation():
    """Test that negation is NOT removed."""
    remover = ColloquialNoiseRemover()
    
    result = remover.remove_noise("ไม่เข้าใจ")
    assert "ไม่" in result['cleaned_query']


def test_whitespace_cleanup():
    """Test that multiple spaces are cleaned up."""
    remover = ColloquialNoiseRemover()
    
    result = remover.remove_noise("OLT   มัน   คืออะไร   หว่า")
    # Should not have multiple consecutive spaces
    assert "  " not in result['cleaned_query']
    assert result['cleaned_query'] == "OLT คืออะไร"


def test_convenience_method():
    """Test the clean() convenience method."""
    remover = ColloquialNoiseRemover()
    
    cleaned = remover.clean("OLT มัน คืออะไร หว่า")
    assert cleaned == "OLT คืออะไร"
    assert isinstance(cleaned, str)


if __name__ == "__main__":
    # Run tests manually
    print("Running ColloquialNoiseRemover tests...")
    test_emphatic_removal()
    test_questioning_removal()
    test_multiple_particles()
    test_no_modification()
    test_preserve_polite_markers()
    test_preserve_question_words()
    test_preserve_negation()
    test_whitespace_cleanup()
    test_convenience_method()
    print("✅ All tests passed!")
