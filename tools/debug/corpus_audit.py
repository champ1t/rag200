import sys
import os
import json

# Add src to path
sys.path.append(os.getcwd())

from src.core.chat_engine import ProcessedCache

class CorpusAuditTool:
    def __init__(self, data_path="data/processed", alias_path="data/aliases.json"):
        print("[AUDIT] Loading ProcessedCache...")
        self.cache = ProcessedCache(data_path)
        self.cache.load()
        
        # Load Aliases directly source of truth
        try:
            with open(alias_path, "r", encoding="utf-8") as f:
                self.aliases = json.load(f)
            print(f"[AUDIT] Loaded {len(self.aliases)} alias keys from {alias_path}")
        except FileNotFoundError:
            print(f"[ERROR] Alias file not found: {alias_path}")
            sys.exit(1)

    def audit(self):
        print("\n================ SYSTEM CORPUS AUDIT ================")
        missing_count = 0
        total_checks = 0
        
        # Check every target expression in alias values
        # e.g. "ne8000" -> ["huawei ne8000", "ne 8000"]
        # We need to verify if "huawei ne8000" matches ANY document
        
        print(f"{'ALIAS KEY':<15} | {'TARGET TOPIC':<30} | {'STATUS':<15} | {'REASON / ACTION'}")
        print("-" * 100)
        
        for alias_key, targets in self.aliases.items():
            # For each target expansion, at least one should be findable
            # We assume the first target is the 'Primary Topic' 
            primary_topic = targets[0]
            total_checks += 1
            
            # Simulate a deterministic lookup
            # We use the primary topic as the query
            match = self.cache.find_best_article_match(primary_topic)
            
            if match and match.get("match_type") == "deterministic":
                print(f"{alias_key:<15} | {primary_topic:<30} | ✅ FOUND        | Doc: {match['title'][:30]}...")
            else:
                print(f"{alias_key:<15} | {primary_topic:<30} | ❌ MISSING      | Action: Ingest '{primary_topic}'")
                missing_count += 1
                
        print("-" * 100)
        print(f"AUDIT COMPLETE: {total_checks - missing_count}/{total_checks} topics found.")
        
        if missing_count > 0:
            print(f"\n[CRITICAL] {missing_count} Alias Targets have NO corresponding documents.")
            print("System will report MISSING_CORPUS for these queries.")
            exit(1)
        else:
            print("\n[SUCCESS] All Alias Targets are covered by documents.")
            exit(0)

if __name__ == "__main__":
    tool = CorpusAuditTool()
    tool.audit()
