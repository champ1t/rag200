import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

class CorpusChecker:
    def __init__(self, data_path="data/processed"):
        self.cache = ProcessedCache(data_path)
        self.cache.load()
        # Create a set of normalized titles for fast lookup
        self.indexed_titles = set(self.cache._link_index.keys())

    def check_completeness(self, expected_topics):
        print("\n--- Corpus Completeness Check ---")
        missing_count = 0
        
        for topic in expected_topics:
            normalized_topic = self.cache.normalize_for_matching(topic)
            
            # Check for exact match first (normalized)
            found = False
            if normalized_topic in self.indexed_titles:
                found = True
            else:
                # Check fuzzy/subset match if strict fails (for multi-word titles)
                # This mimics the "find_best_article_match" logic partly
                for indexed_title in self.indexed_titles:
                    if normalized_topic in indexed_title: # Simple containment check
                        found = True
                        break
            
            if found:
                print(f"✅ {topic}")
            else:
                print(f"❌ {topic} (MISSING)")
                missing_count += 1
                
        print("-" * 30)
        if missing_count == 0:
            print("🎉 All expected topics are PRESENT.")
        else:
            print(f"⚠️  {missing_count} topics are MISSING from the index.")

if __name__ == "__main__":
    # Define critical topics that MUST be present
    CRITICAL_TOPICS = [
        "Huawei NE8000",
        "ZTE OLT C300",
        "ZTE OLT C320",
        "Cisco ASR920",
        "Add ONU to Huawei",
        "Huawei FTTx", 
        "SBC Huawei", # User mentioned this as critical before
        "WiFi Introduction" 
    ]
    
    checker = CorpusChecker()
    checker.check_completeness(CRITICAL_TOPICS)
