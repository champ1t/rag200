
import json
import os
import time
from datetime import datetime
from collections import defaultdict

class MetricsTracker:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.transaction_log = os.path.join(log_dir, "query_metrics.jsonl")
        self.stats_file = os.path.join(log_dir, "dashboard_stats.json")
        self.stats = self._load_stats()
        
    def _load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "total_queries": 0,
            "blocked_queries": 0,
            "missing_article_queries": 0,
            "article_served_queries": 0,
            "cross_vendor_block_count": 0,
            "intents": defaultdict(int),
            "vendors": defaultdict(int)
        }

    def _save_stats(self):
        # Calculate derived metrics
        total = self.stats["total_queries"]
        if total > 0:
            self.stats["derived"] = {
                "blocked_rate": f"{(self.stats['blocked_queries'] / total)*100:.1f}%",
                "missing_rate": f"{(self.stats['missing_article_queries'] / total)*100:.1f}%",
                "success_rate": f"{(self.stats['article_served_queries'] / total)*100:.1f}%"
            }
            
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

    def log(self, query, intent, result, vendor=None, model=None, route=None):
        """
        Log a query transaction and update aggregate stats.
        result: BLOCK | ARTICLE_OK | MISSING
        """
        timestamp = datetime.now().isoformat()
        
        # 1. Append to Transaction Log
        entry = {
            "timestamp": timestamp,
            "query": query,
            "intent": intent,
            "vendor": vendor,
            "model": model,
            "result": result,
            "route": route
        }
        
        with open(self.transaction_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
        # 2. Update Aggregates
        self.stats["total_queries"] += 1
        self.stats["intents"][intent] += 1
        if vendor:
            self.stats["vendors"][vendor] += 1
            
        if result == "BLOCK":
            self.stats["blocked_queries"] += 1
            if route == "blocked_scope": # Heuristic for cross-vendor
                 pass # logic handled by caller or inferred? 
                 # Task says "cross_vendor_block_count". 
                 # If route is blocked_scope, likely cross-vendor or opinion.
                 # Let's trust the caller to pass specific flag or infer from route.
                 
            if route == "blocked_scope":
                self.stats["cross_vendor_block_count"] += 1
                
        elif result == "MISSING":
            self.stats["missing_article_queries"] += 1
            
        elif result == "ARTICLE_OK":
            self.stats["article_served_queries"] += 1
            
        self._save_stats()
