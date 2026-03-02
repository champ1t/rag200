#!/usr/bin/env python3
"""
Step 17.1: Verify normalize_smc_url restoration
"""
import sys
import os
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

print("=" * 80)
print("STEP 17.1: VERIFY normalize_smc_url RESTORATION")
print("=" * 80)

# Create minimal config
config = {
    "hardening": {"enabled": True},
    "retrieval": {"top_k": 5},
    "llm": {"model": "gpt-4o"},
    "vector_store": {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
}

try:
    engine = ChatEngine(config)
    
    # Test the method exists
    assert hasattr(engine, 'normalize_smc_url'), "❌ normalize_smc_url method not found"
    print("✓ normalize_smc_url method exists")
    
    # Test URL normalization
    test_cases = [
        ("http://10.192.133.33/smc/index.php?option=com_content&=article&id=123", 
         "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=123"),
        ("http://example.com/page", "http://example.com/page"),  # No change needed
        ("", ""),  # Empty string
    ]
    
    for input_url, expected in test_cases:
        result = engine.normalize_smc_url(input_url)
        assert result == expected, f"❌ Failed: {input_url} -> {result} (expected {expected})"
        print(f"✓ {input_url[:50]}... -> normalized correctly")
    
    print("\n" + "=" * 80)
    print("✅ STEP 17.1 PASSED: normalize_smc_url restored and functional")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ STEP 17.1 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
