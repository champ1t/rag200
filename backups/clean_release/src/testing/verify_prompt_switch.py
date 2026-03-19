
from src.rag.article_interpreter import ArticleInterpreter
import sys

# Mock
interpreter = ArticleInterpreter(llm_cfg={"model": "test", "base_url": "http://localhost:11434"})

print("=== Phase 122 Verification: Prompt Switching ===\n")

# Test 1: Tutorial Mode
query_b = "ทำความรู้จัก EtherChannel"
# Logic duplication for test setup (since interpret doesn't return the prompt string usually, we mock the call or inspect logic)
# Actually interpret calls ollama_generate. I can mock ollama_generate on the instance to capture the prompt.

# Capture
captured_system = None
def mock_generate(*args, **kwargs):
    global captured_system
    captured_system = kwargs.get('system')
    return "Mock Answer"

# Patch
original_generate = interpreter.interpret
# Wait, interpret calls ollama_generate which is imported. 
# I need to patch the global ollama_generate in article_interpreter module.
from unittest.mock import patch

with patch('src.rag.article_interpreter.ollama_generate', side_effect=mock_generate):
    print(f"Testing Query: '{query_b}'")
    # This should trigger Type B logic (hoisted keyword check)
    # Content must be long enough to pass is_navigation_dominated (>200 chars or structure)
    long_content = "EtherChannel is a port link aggregation technology. " * 20
    interpreter.interpret(query_b, "Title", "URL", long_content)
    
    if captured_system and "Technical Documentation Summarizer" in captured_system:
        print("[PASS] Type B Prompt Used.")
        print(f"Snippet: {captured_system[:100]}...")
    else:
        print("[FAIL] Type B Prompt NOT Used.")
        print(f"Captured: {captured_system[:100] if captured_system else 'None'}...")

print("\n--------------------------------\n")

# Test 2: Normal Mode
query_a = "SBC IP Address"
captured_system = None
with patch('src.rag.article_interpreter.ollama_generate', side_effect=mock_generate):
    print(f"Testing Query: '{query_a}'")
    # Should use default prompt
    long_content_a = "SBC IP Address configuration involves setting up interfaces. " * 20
    interpreter.interpret(query_a, "Title", "URL", long_content_a)
    
    if captured_system and "Enterprise Knowledge Article Interpreter" in captured_system:
        print("[PASS] Type A Prompt Used.")
    else:
        print("[FAIL] Type A Prompt NOT Used.")
        print(f"Captured: {captured_system[:100] if captured_system else 'None'}...")

print("\n=== End Verification ===")
