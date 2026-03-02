import unittest
import sys
import os
import shutil
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.vectorstore.bm25 import SimpleBM25
from src.vectorstore.chroma import ChromaVectorStore

TEST_DIR = "data/tune_vectorstore"
BM25_PATH = "data/tune_bm25.json"

class TestAlphaTuning(unittest.TestCase):
    def setUp(self):
        if Path(TEST_DIR).exists(): shutil.rmtree(TEST_DIR)
        if Path(BM25_PATH).exists(): os.remove(BM25_PATH)

    def tearDown(self):
        if Path(TEST_DIR).exists(): shutil.rmtree(TEST_DIR)
        if Path(BM25_PATH).exists(): os.remove(BM25_PATH)

    def test_alpha_sweep(self):
        """Run Alpha Sweep for Technical vs Semantic queries."""
        vs = ChromaVectorStore(persist_dir=TEST_DIR, collection_name="tune_alpha", bm25_path=BM25_PATH)
        
        # Dataset: 
        # 1. Technical (Keyword heavy)
        # 2. Semantic (Concept heavy)
        docs = [
            # Technical
            "Error 503 is caused by upstream timeout.",
            "VLAN 100 management interface config.",
            # Semantic
            "The system is down due to network congestion.",
            "How to fix internet connection problems."
        ]
        ids = ["err503", "vlan100", "congestion", "fix_internet"]
        metas = [{"cat": "tech"}, {"cat": "tech"}, {"cat": "general"}, {"cat": "general"}]
        
        vs.upsert(ids, docs, metas)
        
        queries = [
            ("Error 503", "arr503"), # Target: Technical
            ("Internet slow", "congestion") # Target: Semantic
        ]
        
        alphas = [0.3, 0.5, 0.7] # Keyword-focused <-> Vector-focused
        
        print("\n=== Alpha Tuning Results ===")
        for q, expected in queries:
            print(f"\nQuery: '{q}' (Target: {expected})")
            for alpha in alphas:
                res = vs.hybrid_query(q, top_k=1, alpha=alpha)
                if not res:
                    print(f"  Alpha {alpha}: No results")
                    continue
                    
                top_doc = res[0].text
                score = res[0].score
                
                # Check hit
                hit = False
                if expected == "arr503" and "Error 503" in top_doc: hit = True
                if expected == "congestion" and ("congestion" in top_doc or "internet" in top_doc): hit = True
                if expected == "vlan100" and "VLAN 100" in top_doc: hit = True
                
                print(f"  Alpha {alpha}: Score={score:.4f} | Hit={hit} | Doc='{top_doc[:40]}...'")

if __name__ == "__main__":
    unittest.main()
