#!/usr/bin/env python3
"""
Phase 3.5: Configuration Hardening Verification
Tests locked parameters, fail-closed logic, and audit logging.
"""
import sys
import os
import yaml
import json
from unittest.mock import MagicMock, patch
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine

# Load valid config for tests
with open("configs/config.yaml", encoding="utf-8") as f:
    VALID_CONFIG = yaml.safe_load(f)

def test_fail_closed_missing_policy():
    """Test system HALTS if routing policy is missing"""
    print("\n🧪 Testing Fail-Closed on Missing Policy...")
    
    # Mock Path.exists to fail ONLY for routing policy
    # autospec=True ensures self is passed as first arg
    def side_effect_exists(self, *args, **kwargs):
        path_str = str(self)
        if "routing_policy_v1.yaml" in path_str:
            return False
        return True # Default to True for other resources
    
    with patch("pathlib.Path.exists", side_effect=side_effect_exists, autospec=True):
        try:
            ChatEngine(cfg=VALID_CONFIG)
            print("❌ FAIL: System started despite missing policy")
            return False
        except RuntimeError as e:
            if "System Halt" in str(e):
                print(f"✅ PASS: System halted as expected: {e}")
                return True
            else:
                print(f"❌ FAIL: Unexpected error: {e}")
                return False

def test_fail_closed_missing_hardening():
    """Test system HALTS if smc_hardening section is missing"""
    print("\n🧪 Testing Fail-Closed on Missing Hardening Section...")
    
    # Policy without hardening section
    mock_policy = {"position_lookup": {}}
    
    def side_effect_exists(self, *args, **kwargs):
        return True # Everything exists
        
    def side_effect_read(self, *args, **kwargs):
        path_str = str(self)
        if "routing_policy_v1.yaml" in path_str:
            return yaml.dump(mock_policy)
        # For other files, try to read real file if possible, or return empty valid json
        if "jsonl" in path_str or "json" in path_str:
             return "" 
        return ""
    
    with patch("pathlib.Path.exists", side_effect=side_effect_exists, autospec=True), \
         patch("pathlib.Path.read_text", side_effect=side_effect_read, autospec=True):
        
        try:
            ChatEngine(cfg=VALID_CONFIG)
            print("❌ FAIL: System started despite missing smc_hardening")
            return False
        except RuntimeError as e:
            if "Security Policy Violation" in str(e):
                print(f"✅ PASS: System halted as expected: {e}")
                return True
            else:
                print(f"❌ FAIL: Unexpected error: {e}")
                return False

def test_audit_logging_enforcement():
    """Test that process() wrapper logs audit data"""
    print("\n🧪 Testing Audit Logging Enforcement...")
    
    # Init engine with valid policy
    valid_policy = {
        "smc_hardening": {
            "enabled": True,
            "similarity_threshold": 0.88,
            "logging": {"audit_route": True}
        }
    }
    
    def side_effect_read(self, *args, **kwargs):
        path_str = str(self)
        if "routing_policy_v1.yaml" in path_str:
            return yaml.dump(valid_policy)
        if "jsonl" in path_str or "json" in path_str:
             return ""
        return ""

    with patch("pathlib.Path.read_text", side_effect=side_effect_read, autospec=True):
        
        # We need to mock build_vectorstore and ProcessedCache to avoid real loading overhead
        # Also mock SemanticCache to avoid importlib metadata issues with sentence-transformers
        with patch("src.chat_engine.build_vectorstore"), \
             patch("src.chat_engine.ProcessedCache"), \
             patch("src.chat_engine.SemanticCache"), \
             patch("src.chat_engine.load_records", return_value=[]):
             
            engine = ChatEngine(cfg=VALID_CONFIG)
            
            # Verify threshold enforced
            if getattr(engine, "hardening_threshold", 0) == 0.88:
                print("✅ PASS: Hardening threshold enforced (0.88)")
            elif getattr(engine, "hardening_threshold", 0) == 0:
                print("❌ FAIL: Hardening threshold not set (0)")
                return False
            else:
                print(f"❌ FAIL: Threshold mismatch. Got {getattr(engine, 'hardening_threshold', 'N/A')}")
                return False
                
            # Mock _process_logic result
            mock_res = {"route": "mock_route", "hits": [], "answer": "ok", "block_reason": "TEST_BLOCK"}
            engine._process_logic = MagicMock(return_value=mock_res)
            
            # Mock _log_audit
            engine._log_audit = MagicMock()
            
            # Call process
            engine.process("test query")
            
            # Check if _log_audit was called
            if engine._log_audit.called:
                print("✅ PASS: _log_audit called by wrapper")
                args = engine._log_audit.call_args[0]
                if args[0] == mock_res:
                    print("✅ PASS: Correct result passed to logger")
                    return True
            else:
                print("❌ FAIL: _log_audit NOT called")
                return False

def main():
    print("=" * 70)
    print("PHASE 3.5: CONFIGURATION HARDENING VERIFICATION")
    print("=" * 70)
    
    results = []
    results.append(test_fail_closed_missing_policy())
    results.append(test_fail_closed_missing_hardening())
    results.append(test_audit_logging_enforcement())
    
    # Summary
    print("\n" + "=" * 70)
    
    passed_count = sum(1 for p in results if p)
    if passed_count == 3:
        print("🎉 ALL CONFIG HARDENING TESTS PASSED!")
        return 0
    else:
        print(f"⚠️  {3 - passed_count} TES(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
