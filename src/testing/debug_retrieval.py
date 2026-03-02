
import sys
import os
import json
import yaml

# Add project root to path
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine

def debug_retrieval():
    # Load Real Config
    with open("configs/config.yaml", "r") as f:
        real_cfg = yaml.safe_load(f)
    
    print("\n[Debug] Initializing ChatEngine with REAL config...")
    engine = ChatEngine(real_cfg)
    
    queries = [
        "Huawei bras ippgw command มีอะไรบ้าง",
        "วิธี clear ip address ลูกค้าใน IP Pool"
    ]

    print(f"--- VectorStore Stats ---")
    try:
        if hasattr(engine.vs, "collection"):
            print(f"Chroma Collection Count: {engine.vs.collection.count()}")
    except Exception as e:
        print(f"Chroma Error: {e}")

    try:
        print(f"BM25 Corpus Size: {engine.vs.bm25.corpus_size}")
        print(f"BM25 Avg DL: {engine.vs.bm25.avg_dl}")
        print(f"Tokenization Test 'Huawei': {engine.vs.bm25.tokenize('Huawei')}")
        print(f"Tokenization Test 'IPPgw': {engine.vs.bm25.tokenize('IPPgw')}")
    except Exception as e:
        print(f"BM25 Error: {e}")

    for query in queries:
        print(f"\n--- Debug Retrieval: {query} ---")
        # Access VectorStore directly
        hits = engine.vs.hybrid_query(query, top_k=20)
        
        print(f"Found {len(hits)} hits.")
        for i, h in enumerate(hits):
            meta = h.metadata or {}
            title = meta.get("title", "NoTitle")
            url = meta.get("url", "NoURL")
            score = h.score
            
            print(f"{i+1}. [{score:.4f}] {title} ({url})")
            
            # Check if this is Article 670
            if "Huawei bras ippgw command" in title or "670" in url:
                print(f"   *** TARGET FOUND ***")

if __name__ == "__main__":
    debug_retrieval()
