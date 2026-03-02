import sys
import os
import inspect

# Add current directory to path
sys.path.append(os.getcwd())

print(f"Current WD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    from src.core.chat_engine import ChatEngine
    print(f"ChatEngine File: {inspect.getfile(ChatEngine)}")
    
    # Inspect source of _process_logic
    src_lines, start_line = inspect.getsourcelines(ChatEngine._process_logic)
    print(f"_process_logic starts at line {start_line}")
    print("First 20 lines of _process_logic source:")
    for i, line in enumerate(src_lines[:20]):
        print(f"{start_line+i}: {line.rstrip()}")

    # Instantiate and run
    print("\n--- Instantiating ChatEngine ---")
    mock_cfg = {
        "llm": {"model": "mock", "base_url": "mock"},
        "chat": {"show_context": False},
        "rag": {"use_cache": False}, 
        "retrieval": {"top_k": 3}
    }
    
    # We need to mock dependencies to avoid loading everything
    # But for this test, let's see if we can instantiate without heavy mocks if possible
    # Or apply minimal patching manually
    
    # Manual patch for initialization
    from unittest.mock import MagicMock
    import src.chat_engine
    
    src.chat_engine.build_vectorstore = MagicMock()
    src.chat_engine.load_records = MagicMock(return_value=[])
    src.chat_engine.WebHandler = MagicMock()
    src.chat_engine.ProcessedCache = MagicMock() # Use mock cache to avoid loading real data
    
    engine = ChatEngine(mock_cfg)
    
    # Mock processed_cache instance methods to prevent fast crash
    engine.processed_cache.normalize_for_matching.return_value = "nomatch"
    engine.processed_cache._normalized_title_index = {}
    engine.processed_cache.find_best_article_match.return_value = {
        "match_type": "deterministic",
        "title": "Test Title",
        "url": "http://test",
        "score": 1.0,
        "text": "Test Content"
    }

    print("\n--- Calling process() ---")
    res = engine.process("test query")
    print(f"Result Route: {res.get('route')}")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
