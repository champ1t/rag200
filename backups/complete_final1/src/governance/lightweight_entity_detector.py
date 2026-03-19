"""
Lightweight Entity Detector - Phase 27.4 Bug Fix

Purpose:
Fast entity detection BEFORE query normalization to prevent entity stripping.

Entities Detected:
- Devices: OLT, ONU, UMUX, BRAS, PE, APE, LPE, Router, Switch, NE8000
- Locations: หาดใหญ่, ชุมพร, สุราษฎร์ธานี, ภูเก็ต, กระบี่, ตรัง, สตูล, ปัตตานี
- Organizations: SMC, OMC, RNOC, NOC, CSOC, กบป.
- Technical Terms: VLAN, GPON, XGS-PON, Fiber, IP, PPPoE, VAS

Performance: <1ms (regex-based, no LLM)
"""

import re
from typing import Dict, Any


class LightweightEntityDetector:
    """
    Fast regex-based entity detector for bypassing noise gate.
    
    Use Case:
    Query: "ขอเบอร์UMUX"
    Without entity detection: QueryNormalizer strips "UMUX" → blocked by noise gate
    With entity detection: Detects "UMUX" BEFORE normalization → bypass noise gate → success
    """
    
    def __init__(self):
        """Initialize entity patterns."""
        
        # Device patterns (case-insensitive)
        self.device_patterns = [
            r'\b(OLT|ONT|ONU)\b',
            r'\b(UMUX|U-MUX|UMAX)\b',
            r'\b(BRAS|BAS)\b',
            r'\b(PE|APE|LPE)\b',
            r'\b(Router|Switch)\b',
            r'\b(NE8000|NE40|NE20)\b',
            r'\b(MA5800|MA5600|MA5683)\b',  # Huawei OLT models
            r'\b(CX600|AN5516)\b',  # ZTE OLT models
        ]
        
        # Location patterns (Thai cities/provinces)
        self.location_patterns = [
            r'(หาดใหญ่|Hat\s*Yai)',
            r'(ชุมพร|Chumphon)',
            r'(สุราษฎร์ธานี|Surat\s*Thani)',
            r'(ภูเก็ต|Phuket)',
            r'(กระบี่|Krabi)',
            r'(ตรัง|Trang)',
            r'(สตูล|Satun)',
            r'(ปัตตานี|Pattani)',
            r'(ยะลา|Yala)',
            r'(นราธิวาส|Narathiwat)',
            r'(พังงา|Phang\s*Nga)',
            r'(ระนอง|Ranong)',
        ]
        
        # Organization patterns
        self.organization_patterns = [
            r'\b(SMC|smc)\b',
            r'\b(OMC|omc)\b',
            r'\b(RNOC|rnoc)\b',
            r'\b(NOC|noc)\b',
            r'\b(CSOC|csoc)\b',
            r'\b(UMUX|umux)\b',
            r'(กบป\.|กบป)',  # Government organization
        ]
        
        # Technical term patterns
        self.technical_patterns = [
            r'\b(VLAN|vlan)\b',
            r'\b(GPON|gpon)\b',
            r'\b(XGS-PON|xgs-pon)\b',
            r'\b(Fiber|fiber)\b',
            r'\b(IP|ip)\b',
            r'\b(PPPoE|pppoe)\b',
            r'\b(VAS|vas)\b',
            r'\b(MPLS|mpls)\b',
            r'\b(BGP|bgp)\b',
            r'\b(OSPF|ospf)\b',
        ]
        
        # Compile all patterns for performance
        self.compiled_patterns = {
            'DEVICE': [re.compile(p, re.IGNORECASE) for p in self.device_patterns],
            'LOCATION': [re.compile(p, re.IGNORECASE) for p in self.location_patterns],
            'ORGANIZATION': [re.compile(p, re.IGNORECASE) for p in self.organization_patterns],
            'TECHNICAL': [re.compile(p, re.IGNORECASE) for p in self.technical_patterns],
        }
    
    def detect(self, query: str) -> Dict[str, Any]:
        """
        Detect entities in query.
        
        Args:
            query: User query string
        
        Returns:
            {
                'has_entity': bool,
                'entity_value': str,  # e.g., "UMUX"
                'entity_type': str,   # e.g., "DEVICE"
                'confidence': float,  # 0.6-1.0
                'all_entities': list  # All detected entities
            }
        """
        all_entities = []
        
        # Check each pattern type
        for entity_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(query)
                for match in matches:
                    entity_value = match.group(0)
                    all_entities.append({
                        'value': entity_value,
                        'type': entity_type,
                        'start': match.start(),
                        'end': match.end()
                    })
        
        # Return result
        if all_entities:
            # Use first entity as primary
            primary = all_entities[0]
            
            # Calculate confidence based on entity type and query length
            confidence = self._calculate_confidence(primary, query)
            
            return {
                'has_entity': True,
                'entity_value': primary['value'],
                'entity_type': primary['type'],
                'confidence': confidence,
                'all_entities': all_entities
            }
        else:
            return {
                'has_entity': False,
                'entity_value': None,
                'entity_type': None,
                'confidence': 0.0,
                'all_entities': []
            }
    
    def _calculate_confidence(self, entity: Dict, query: str) -> float:
        """
        Calculate confidence score for entity detection.
        
        Factors:
        - Entity type (DEVICE/ORGANIZATION = higher confidence)
        - Entity length vs query length ratio
        - Position in query (earlier = higher confidence)
        """
        base_confidence = {
            'DEVICE': 0.85,
            'ORGANIZATION': 0.80,
            'LOCATION': 0.75,
            'TECHNICAL': 0.70,
        }
        
        confidence = base_confidence.get(entity['type'], 0.60)
        
        # Boost if entity is significant portion of query
        entity_len = len(entity['value'])
        query_len = len(query)
        if query_len > 0:
            ratio = entity_len / query_len
            if ratio > 0.3:  # Entity is >30% of query
                confidence = min(1.0, confidence + 0.10)
        
        # Boost if entity is at start of query
        if entity['start'] < 5:
            confidence = min(1.0, confidence + 0.05)
        
        return round(confidence, 2)
    
    def should_bypass_noise_gate(self, query: str, min_confidence: float = 0.70) -> bool:
        """
        Convenience method: Should this query bypass noise gate?
        
        Args:
            query: User query
            min_confidence: Minimum confidence threshold (default 0.70)
        
        Returns:
            True if entity detected with sufficient confidence
        """
        result = self.detect(query)
        return result['has_entity'] and result['confidence'] >= min_confidence


# ============================================================================
# Unit Tests (run with: python3 -m pytest src/governance/lightweight_entity_detector.py -v)
# ============================================================================

def test_device_detection():
    """Test device entity detection."""
    detector = LightweightEntityDetector()
    
    # Test UMUX
    result = detector.detect("ขอเบอร์UMUX")
    assert result['has_entity'] == True
    assert result['entity_type'] == 'DEVICE'
    assert 'UMUX' in result['entity_value'].upper()
    assert result['confidence'] >= 0.70
    
    # Test OLT
    result = detector.detect("คู่มือ OLT")
    assert result['has_entity'] == True
    assert result['entity_type'] == 'DEVICE'
    
    # Test NE8000
    result = detector.detect("Huawei NE8000 Command Manual")
    assert result['has_entity'] == True


def test_location_detection():
    """Test location entity detection."""
    detector = LightweightEntityDetector()
    
    # Test หาดใหญ่
    result = detector.detect("ขอเบอร์หาดใหญ่")
    assert result['has_entity'] == True
    assert result['entity_type'] == 'LOCATION'
    assert 'หาดใหญ่' in result['entity_value']
    
    # Test ภูเก็ต
    result = detector.detect("ศูนย์ภูเก็ต")
    assert result['has_entity'] == True


def test_organization_detection():
    """Test organization entity detection."""
    detector = LightweightEntityDetector()
    
    # Test CSOC
    result = detector.detect("ขอเบอร์ CSOC")
    assert result['has_entity'] == True
    assert result['entity_type'] == 'ORGANIZATION'
    
    # Test OMC
    result = detector.detect("OMC คือใคร")
    assert result['has_entity'] == True


def test_technical_detection():
    """Test technical term detection."""
    detector = LightweightEntityDetector()
    
    # Test GPON
    result = detector.detect("GPON คืออะไร")
    assert result['has_entity'] == True
    assert result['entity_type'] == 'TECHNICAL'
    
    # Test VLAN
    result = detector.detect("config VLAN")
    assert result['has_entity'] == True


def test_no_entity():
    """Test queries without entities."""
    detector = LightweightEntityDetector()
    
    # Test greeting
    result = detector.detect("สวัสดีครับ")
    assert result['has_entity'] == False
    assert result['entity_value'] is None
    
    # Test general question
    result = detector.detect("ช่วยบอกหน่อย")
    assert result['has_entity'] == False


def test_multiple_entities():
    """Test queries with multiple entities."""
    detector = LightweightEntityDetector()
    
    result = detector.detect("ขอเบอร์ CSOC หาดใหญ่")
    assert result['has_entity'] == True
    assert len(result['all_entities']) >= 2  # CSOC + หาดใหญ่


def test_bypass_decision():
    """Test bypass noise gate decision."""
    detector = LightweightEntityDetector()
    
    # Should bypass
    assert detector.should_bypass_noise_gate("ขอเบอร์UMUX") == True
    assert detector.should_bypass_noise_gate("คู่มือ OLT") == True
    
    # Should NOT bypass
    assert detector.should_bypass_noise_gate("สวัสดี") == False
    assert detector.should_bypass_noise_gate("ช่วยหน่อย") == False


if __name__ == "__main__":
    # Run tests manually
    print("Running LightweightEntityDetector tests...")
    test_device_detection()
    test_location_detection()
    test_organization_detection()
    test_technical_detection()
    test_no_entity()
    test_multiple_entities()
    test_bypass_decision()
    print("✅ All tests passed!")
