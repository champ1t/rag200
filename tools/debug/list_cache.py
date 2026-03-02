import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

def list_cache_keys():
    cache = ProcessedCache("data/processed")
    cache.load()
    
    print("\n--- Listing Cache Keys (Titles) ---")
    keys = sorted(cache._link_index.keys())
    for k in keys:
        if "ne8000" in k or "huawei" in k or "676" in k:
            print(f"FOUND: {k}")
            
    # Also check URLs in values
    print("\n--- Checking URLs for ID 676 ---")
    found_urls = False
    for k, entries in cache._link_index.items():
        for entry in entries:
            href = entry.get("href", "")
            if "id=676" in href or "id=676" in entry.get("source", ""):
                print(f"FOUND URL (ID 676): {href} (Title: {entry.get('text')})")
                found_urls = True
                
    if not found_urls:
        print("URL with id=676 NOT FOUND in cache.")

if __name__ == "__main__":
    list_cache_keys()
