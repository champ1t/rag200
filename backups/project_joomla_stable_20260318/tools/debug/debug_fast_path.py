import sys
import os
sys.path.append(os.getcwd())
from src.core.chat_engine import ChatEngine
from src.directory.lookup import lookup_phones, precompute_record
import yaml

def main():
    cfg = yaml.safe_load(open("configs/config.yaml"))
    engine = ChatEngine(cfg)
    records = engine.records
    for r in records: precompute_record(r)
    
    q = "สื่อสารข้อมูล ภูเก็ต"
    print(f"Query: {q}")
    hits = lookup_phones(q, records)
    if hits:
        top = hits[0]
        print(f"Top Hit: {top.get('name')} | Score: {top.get('_score')} | Type: {top.get('_match_type')}")
    else:
        print("No hits found.")

if __name__ == "__main__":
    main()
