import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ingest.process_one import process_raw_html_file
from src.ingest.state import load_state, save_state, set_page_hash

def reprocess_all():
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    
    if not raw_dir.exists():
        print("No raw data found.")
        return

    files = list(raw_dir.glob("*.html"))
    print(f"Found {len(files)} raw files to reprocess...")
    
    # We need to recover the original URL from the raw content or filename if possible?
    # Actually `process_raw_html_file` needs the source URL.
    # In `data/processed` the JSONs have the "url" field. We can map filename -> url from existing processed files.
    
    # Map raw_stem -> url
    stem_to_url = {}
    for json_file in processed_dir.glob("*.json"):
        try:
            import json
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if "raw_file" in data and "url" in data:
                raw_path = Path(data["raw_file"])
                stem_to_url[raw_path.stem] = data["url"]
        except Exception:
            continue
            
    print(f"Mapped {len(stem_to_url)} files to URLs.")

    count = 0
    errors = 0
    state = load_state() # We might update hashes? Actually if text structure changes (which it shouldn't for body text, but we added links field), we might not strictly need to update hash unless downstream depends on it. 
    # But `process_one` returns new hash. Let's just run it.

    for raw_file in files:
        if raw_file.stem not in stem_to_url:
            print(f"[SKIP] No URL found for {raw_file.name}")
            continue
            
        url = stem_to_url[raw_file.stem]
        try:
            # Re-run processing
            out_file, new_hash = process_raw_html_file(str(raw_file), str(processed_dir), url)
            # Update state with new hash just in case
            set_page_hash(state, url, new_hash)
            count += 1
            if count % 10 == 0:
                print(f"Processed {count}...")
        except Exception as e:
            print(f"[ERR] {raw_file.name}: {e}")
            errors += 1
            
    save_state(state)
    print(f"Done. Processed {count}, Errors {errors}")

if __name__ == "__main__":
    reprocess_all()
    
    # Rebuild Records (Contacts & Positions)
    print("\n[INFO] Rebuilding Directory Records...")
    from src.directory.build_records import build_directory_records
    build_directory_records("data/processed", "Itemid=61", "data/records/directory.jsonl")
    
    print("\n[INFO] Extracting Positions...")
    from src.directory.extract_positions import extract_positions
    extract_positions()
    
    print("\n[INFO] Finalization Complete.")
