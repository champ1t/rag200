
import sys
import os
sys.path.append(os.getcwd())

from src.rag.article_cleaner import clean_article_html, extract_topic_anchored_facts
from src.rag.article_interpreter import ArticleInterpreter
# from src.utils.config_loader import load_config # Not needed for this standalone test
import json
import re

def repro_onu_zte():
    # Load raw content
    raw_path = "data/raw/10.192.133.33_smc_index.php_option_com_content_view_article_id_599_-onu-zte-_catid_43_2011-11-14-08-37-12_Itemid_81.html"
    
    if not os.path.exists(raw_path):
        print(f"Error: File not found: {raw_path}")
        return

    with open(raw_path, 'r', encoding='utf-8') as f:
        html = f.read()

    print(f"Loaded {len(html)} chars from {raw_path}")
    
    # 1. Clean
    cleaned, _, _ = clean_article_html(html)
    print("\n--- Cleaned Preview (First 500) ---")
    print(cleaned[:500])
    
    # 2. Extract Facts
    facts = extract_topic_anchored_facts(cleaned, "onu zte")
    print(f"\n--- Extracted Facts ({len(facts)}) ---")
    for i, f in enumerate(facts):
        print(f"[{i+1}] {f[:200]}...") # Truncate for readability
        
    # 3. Interpreter Logic (Fast Path) - Simulation
    print("\n--- ArticleInterpreter Simulation ---")
    
    # Duplicate existing logic from ArticleInterpreter.process_one
    # We want to reproduce the mess first
    
    # Simulate the duplicate lines issue
    
    deduped = []
    seen = set()
    
    for f in facts:
        # Basic dedup
        if f in seen: continue
        
        # New Filter: Remove Table Rows?
        if re.match(r'^\|\s*\d+\s*\|\s*\d+\s*\|', f):
            print(f"[Dropped Table Row] {f[:50]}")
            continue
            
        # New Filter: Remove "Written by" mid-content
        if "เขียนโดย" in f and len(f) < 100:
             print(f"[Dropped Metadata] {f}")
             continue

        formatted_fact = f
        # Apply bullet point if missing
        if not f.startswith("- ") and not f[0].isdigit():
             formatted_fact = f"- {f}"
             
        deduped.append(formatted_fact)
        seen.add(f)
            
    print(f"\nDeduped Count: {len(deduped)}")
    for i, f in enumerate(deduped):
        print(f"[{i+1}] {f}")

if __name__ == "__main__":
    repro_onu_zte()
