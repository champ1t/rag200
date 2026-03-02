#!/usr/bin/env python3
"""
Test Knowledge Type Classifier
Verifies classification logic works correctly
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.knowledge_classifier import classify_knowledge_type, KnowledgeType

def test_classification(query, intent, expected_type, description):
    """Test a single classification"""
    result = classify_knowledge_type(query, intent, {})
    
    passed = result["knowledge_type"] == expected_type
    status = "✅ PASS" if passed else "❌ FAIL"
    
    print(f"\n{status} {description}")
    print(f"  Query: {query}")
    print(f"  Intent: {intent}")
    print(f"  Expected: {expected_type}")
    print(f"  Got: {result['knowledge_type']} (confidence={result['confidence']:.2f})")
    print(f"  Explanation: {result['explanation']}")
    
    return passed

if __name__ == "__main__":
    print("="*60)
    print("KNOWLEDGE TYPE CLASSIFIER - UNIT TESTS")
    print("="*60)
    
    results = []
    
    # Test GENERAL_NETWORK_KNOWLEDGE
    results.append(test_classification(
        "ONU คืออะไร", "DEFINE_TERM", 
        KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
        "Definition query should be GENERAL"
    ))
    
    results.append(test_classification(
        "ไฟ LOS หมายถึงอะไร", "DEFINE_TERM",
        KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
        "Explanation query should be GENERAL"
    ))
    
    results.append(test_classification(
        "VLAN ทำงานยังไง", "DEFINE_TERM",
        KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
        "Principle query should be GENERAL"
    ))
    
    # Test NT_SPECIFIC_PROCEDURE
    results.append(test_classification(
        "ตั้งค่า ONU ยังไง", "HOWTO_PROCEDURE",
        KnowledgeType.NT_SPECIFIC_PROCEDURE,
        "Configuration query should be NT_SPECIFIC"
    ))
    
    results.append(test_classification(
        "วิธีเช็ค ONU status", "HOWTO_PROCEDURE",
        KnowledgeType.NT_SPECIFIC_PROCEDURE,
        "Procedure query should be NT_SPECIFIC"
    ))
    
    results.append(test_classification(
        "คำสั่ง show onu", "HOWTO_PROCEDURE",
        KnowledgeType.NT_SPECIFIC_PROCEDURE,
        "Command query should be NT_SPECIFIC"
    ))
    
    # Test POLICY_OR_CONTACT
    results.append(test_classification(
        "ขอเบอร์ CSOC", "CONTACT_LOOKUP",
        KnowledgeType.POLICY_OR_CONTACT,
        "Contact query should be POLICY_OR_CONTACT"
    ))
    
    results.append(test_classification(
        "ใครคือ ผจ", "POSITION_HOLDER_LOOKUP",
        KnowledgeType.POLICY_OR_CONTACT,
        "Position query should be POLICY_OR_CONTACT"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(results)
    
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL CLASSIFIER TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        sys.exit(1)
