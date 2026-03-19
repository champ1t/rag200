
import sys
import os
sys.path.append(os.getcwd())
from src.chat_engine import ChatEngine

def debug():
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "../../configs/config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print(f"Loaded config from {config_path}")
    engine = ChatEngine(cfg)
    
    q = "แก้ user สำหรับลูกค้า context private"
    print(f"Query: {q}")
    
    print(f"BM25 Corpus Size: {engine.vs.bm25.corpus_size}")
    print(f"Chroma Collection Count: {engine.vs.collection.count()}")
    peek = engine.vs.collection.peek(limit=1)
    if peek['ids']:
        print(f"Sample Chroma ID: {peek['ids'][0]}")
    
    ct = engine.vs.bm25.get_scores("context", top_k=1)
    if ct:
        print("Top BM25 result for 'context':", ct)
    else:
        print("Top BM25 result for 'context': None")
        
    pv = engine.vs.bm25.get_scores("private", top_k=1)
    if pv:
        print("Top BM25 result for 'private':", pv)
        target_id = pv[0][0]
        print(f"Checking Chroma for ID: {target_id}")
        try:
            got = engine.vs.collection.get(ids=[target_id])
            print(f"Chroma has it: {bool(got['ids'])}")
        except Exception as e:
            print(f"Chroma lookup failed: {e}")
    else:
        print("Top BM25 result for 'private': None")
    
    # Spy on hybrid_query to see scores
    hits = engine.vs.hybrid_query(q, top_k=3)
    print(f"Hybrid Query returned {len(hits)} hits.")
    for i, h in enumerate(hits):
        print(f"Hit {i}: Score={h.score:.4f} Title={h.metadata.get('title')} URL={h.metadata.get('url')}")
        
    res = engine.process(q)
    print(f"Route: {res.get('route')}")
    print(f"Answer: {res.get('answer')[:100]}...")

if __name__ == "__main__":
    debug()
