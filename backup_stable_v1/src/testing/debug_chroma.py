
import chromadb
from pathlib import Path

def debug_chroma():
    persist_dir = "data/vectorstore"
    print(f"Connecting to ChromaDB at {persist_dir}...")
    
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        collections = client.list_collections()
        print(f"Found {len(collections)} collections:")
        for c in collections:
            print(f" - Name: {c.name}, Count: {c.count()}")
            
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")

if __name__ == "__main__":
    debug_chroma()
