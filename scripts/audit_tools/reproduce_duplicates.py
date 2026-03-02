import sys
import os
import json
from typing import List, Dict, Any

sys.path.append(os.getcwd())

from src.rag.handlers.contact_handler import ContactHandler
from src.directory.lookup import lookup_phones, strip_query

# Mock DirectoryHandler for dependency
class MockDirectoryHandler:
    def find_person(self, q): return []
    def find_by_role(self, q): return []
    def suggest_roles(self, q): return []

def load_data():
    records = []
    # Load directory
    with open("data/records/directory.jsonl", "r") as f:
        for line in f: records.append(json.loads(line))
    # Load positions (ContactHandler usually merges these or lookup_phones uses them? 
    # Actually lookup_phones simply iterates the list passed to it.
    # In main app, records = directory + positions (concatenated) usually.
    with open("data/records/positions.jsonl", "r") as f:
        for line in f: records.append(json.loads(line))
    return records

def test_prachya():
    records = load_data()
    query = "เบอร์ ปรัชญา"
    
    print(f"--- Testing Query: {query} ---")
    result = ContactHandler.handle(query, records, directory_handler=MockDirectoryHandler())
    
    print("Raw Answer:")
    print(result["answer"])
    
    print("\n--- Hits Analysis ---")
    for hit in result["hits"]:
        print(f"Name: {hit.get('name')}, Role: {hit.get('role', 'N/A')}, Phones: {hit.get('phones')}")

if __name__ == "__main__":
    test_prachya()
