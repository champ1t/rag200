
import sys
import os
import yaml

# Add project root to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ChatEngine
from src.rag.article_interpreter import ArticleInterpreter
from src.rag.article_cleaner import strip_navigation_text

def load_config(path="configs/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_nav_stripping():
    print("\n=== Testing Navigation Stripping (Phase 124) ===")
    
    # 1. Test strip_navigation_text directly
    noise_content = """
    Home | About | Contact | Login | Register
    News | Activity | Gallery
    
    EtherChannel Introduction
    EtherChannel is a port link aggregation technology.
    
    Sidebar Link 1
    Sidebar Link 2
    Sidebar Link 3
    Sidebar Link 4
    Sidebar Link 5
    
    Copyright 2024 NT PLC.
    Designed by Joomla.
    """
    
    print(f"[TEST] Raw Content:\n---\n{noise_content}\n---")
    
    cleaned = strip_navigation_text(noise_content)
    print(f"\n[TEST] Cleaned Content:\n---\n{cleaned}\n---")
    
    # Assertions
    if "Home | About" in cleaned:
        print("[FAIL] Pipe menu not removed.")
    elif "Sidebar Link 1" in cleaned and "Sidebar Link 5" in cleaned: # Heuristic might fail on generic text if not specifically targeted, but let's see
        # Our heuristic relies on "consecutive short lines". 5 lines of "Sidebar Link X" is 14 chars. 
        # Should be removed.
        print("[FAIL] Sidebar block not removed.")
    elif "Joomla" in cleaned:
        print("[FAIL] Footer not removed.")
    else:
        print("[PASS] direct strip_navigation_text working.")

    # 2. Test Integration via ArticleInterpreter
    print("\n[TEST] ArticleInterpreter Integration")
    cfg = load_config()
    chat = ChatEngine(cfg)
    interpreter = chat.article_interpreter
    
    # We will pass the noise_content as if it was fetched
    # Query must trigger Tutorial Mode
    query = "ทำความรู้จัก EtherChannel"
    
    # We expect `interpret` to call `strip_navigation_text`.
    # We can check the logs or output.
    # Since we can't easily spy on the internal call without mocking, 
    # we will rely on the printed logs from ArticleInterpreter which prints content length?
    # Or strict output checking.
    
    # Override read_url_content? No, interpret takes content arg.
    # But wait, `interpret` takes `article_content`. 
    # Does it use it directly? Yes.
    
    # Note: interpret will call LLM. We don't want to wait for LLM if possible, 
    # or we just accept it takes a few seconds.
    # To avoid long wait, we can mock `ollama_generate` or just let it run (timeout is high).
    # Let's let it run but expect a clean summary.
    
    response = interpreter.interpret(
        user_query=query,
        article_title="Test Article",
        article_url="http://mock",
        article_content=noise_content,
        images=[],
        show_images=False
    )
    
    print(f"\n[RESULT] Response: {response[:200]}...")
    
    # If the summary talks about "Sidebar Link", we failed.
    if "Sidebar Link" in response:
        print("[FAIL] Sidebar content leaked into Summary.")
    else:
        print("[PASS] Summary seems clean.")

if __name__ == "__main__":
    test_nav_stripping()
