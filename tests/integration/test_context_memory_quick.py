#!/usr/bin/env python3
"""
Quick Test: Conversation Context Memory

Tests: "ศูนย์หาดใหญ่โทรอะไร" → "ขอเบอร์" should work
"""

import sys
sys.path.insert(0, '/Users/jakkapatmac/Documents/NT/RAG/rag_web')

import yaml
from pathlib import Path

print("=" * 70)
print("Conversation Context Memory - Quick Test")
print("=" * 70)

# Load config
config_path = Path('/Users/jakkapatmac/Documents/NT/RAG/rag_web/configs/config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

from src.core.chat_engine import ChatEngine
engine = ChatEngine(cfg)

print("\n✅ ChatEngine loaded with Context Memory\n")

# Test Case 1: Context creation
print("=" * 70)
print("Test 1: ศูนย์หาดใหญ่โทรอะไร (should create context)")
print("=" * 70)

result1 = engine.process("ศูนย์หาดใหญ่โทรอะไร")
print(f"\nRoute: {result1.get('route')}")
print(f"Answer: {result1.get('answer', '')[:200]}")

if engine.last_context:
    print(f"\n✅ Context saved!")
    print(f"  Entities: {engine.last_context.get('entities', {})}")
    print(f"  Intent: {engine.last_context.get('intent')}")
else:
    print(f"\n❌ No context saved")

# Test Case 2: Context usage
print("\n" + "=" * 70)
print("Test 2: ขอเบอร์ (should use context from Test 1)")
print("=" * 70)

result2 = engine.process("ขอเบอร์")
print(f"\nRoute: {result2.get('route')}")
print(f"Answer: {result2.get('answer', '')[:200]}")

# Check if same results (context applied)
success = False
if "หาดใหญ่" in result2.get('answer', ''):
    print("\n✅ PASS - Context applied! (หาดใหญ่ found in answer)")
    success = True
else:
    print("\n❌ FAIL - Context NOT applied")

print("\n" + "=" * 70)
print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
print("=" * 70)

sys.exit(0 if success else 1)
