#!/usr/bin/env python3
"""
Test script for ContentClassifier
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

from src.ai.content_classifier import ContentClassifier

# Test configuration
llm_cfg = {
    "fast_model": "llama3.2:3b",
    "base_url": "http://localhost:11434"
}

classifier = ContentClassifier(llm_cfg)

# Test cases
test_cases = [
    {
        "title": "VLAN Planning Guide",
        "url": "https://example.com/vlan-guide",
        "content": "VLAN (Virtual LAN) is a network segmentation technique. It allows you to divide a physical network into multiple logical networks. Each VLAN has a unique ID (1-4094). Benefits include improved security, reduced broadcast traffic, and better network organization. To configure a VLAN, you need to assign VLAN IDs to switch ports and configure routing between VLANs if needed.",
        "metadata": {"text_length": 350, "detected_table_rows": 0, "detected_images": 0},
        "expected": "TEXT_ARTICLE"
    },
    {
        "title": "SMC Portal - Links",
        "url": "https://example.com/portal",
        "content": "Quick Links:\n- Dashboard\n- Reports\n- Settings\n- Help\n- Contact\n- About\n- Privacy Policy\n- Terms of Service",
        "metadata": {"text_length": 120, "detected_table_rows": 0, "detected_images": 0},
        "expected": "LINK_MENU"
    },
    {
        "title": "Network Diagram",
        "url": "https://example.com/diagram",
        "content": "[Image: Network topology]\n[Image: Router configuration]\n[Image: Switch layout]\nSee attached diagrams.",
        "metadata": {"text_length": 80, "detected_table_rows": 0, "detected_images": 6},
        "expected": "IMAGE_ONLY"
    },
    {
        "title": "Contact Directory",
        "url": "https://example.com/contacts",
        "content": "Name | Phone | Email | Department\n" + "\n".join([f"Person {i} | 123-456 | email@example.com | Dept {i}" for i in range(60)]),
        "metadata": {"text_length": 2000, "detected_table_rows": 60, "detected_images": 0},
        "expected": "TABLE_HEAVY"
    }
]

print("=== ContentClassifier Test ===\n")

for i, test in enumerate(test_cases, 1):
    print(f"Test {i}: {test['title']}")
    print(f"Expected: {test['expected']}")
    
    result = classifier.classify(
        title=test['title'],
        url=test['url'],
        content=test['content'],
        metadata=test['metadata']
    )
    
    print(f"  Result: {result['content_type']}")
    print(f"  Should Summarize: {result['should_summarize']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Latency: {result['latency_ms']:.1f}ms")
    print(f"  Reason: {result['reason']}")
    
    match = "✓" if result['content_type'] == test['expected'] else "✗"
    print(f"  {match} {'PASS' if match == '✓' else 'FAIL'}")
    print()
