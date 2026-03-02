import sys
import os
import json

sys.path.append(os.getcwd())

from src.rag.handlers.contact_handler import ContactHandler
from src.rag.handlers.directory_handler import DirectoryHandler

def load_data():
    records = []
    with open("data/records/directory.jsonl", "r") as f:
        for line in f: records.append(json.loads(line))
    with open("data/records/positions.jsonl", "r") as f:
        for line in f: records.append(json.loads(line))
    return records

def load_directory_handler(records):
    # Mocking indexes... actually DirectoryHandler logic requires `position_index`.
    # We need to build it roughly or use the real one if we can load it.
    # But `positions.jsonl` IS the position index source?
    # Usually `build_records.py` builds `positions.jsonl`.
    # `DirectoryHandler` takes `position_index` (Dict[role, List[Record]]).
    
    pos_index = {}
    for r in records:
        if r.get("role"):
            role = r["role"]
            if role not in pos_index: pos_index[role] = []
            pos_index[role].append(r)
            
    return DirectoryHandler(pos_index, records)

def test_shadowing():
    records = load_data()
    dh = load_directory_handler(records)
    
    # 1. Query for Name (Should get Supervisor/Merged)
    q1 = "เบอร์ ปรัชญา"
    print(f"\n--- Test 1: {q1} ---")
    r1 = ContactHandler.handle(q1, records, directory_handler=dh)
    print(r1["answer"])
    
    # 2. Query for Role (Should get ผจ.สบลตน.)
    q2 = "เบอร์ ผจ.สบลตน."
    print(f"\n--- Test 2: {q2} ---")
    r2 = ContactHandler.handle(q2, records, directory_handler=dh)
    print(r2["answer"])
    
    # 3. Query for Member (Should get FTTx if specific?)
    # "เบอร์ งาน FTTx" -> Should list members.
    q3 = "เบอร์ งาน FTTx"
    print(f"\n--- Test 3: {q3} ---")
    r3 = ContactHandler.handle(q3, records, directory_handler=dh)
    print(r3["answer"][:500]) # Truncate

if __name__ == "__main__":
    test_shadowing()
