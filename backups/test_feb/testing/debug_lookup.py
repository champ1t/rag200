import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.directory.lookup import load_records, lookup_phones
from src.chat_engine import ChatEngine

records = load_records("data/records/directory.jsonl")

name = "นายสมบูรณ์" # Guessing part of name
print(f"Lookup '{name}':")
hits = lookup_phones(name, records)
for h in hits:
    print(f"- {h['name']} {h['phones']}")

# Try the full string from position lookup
# I need to know EXACTLY what name is returned by position lookup.
# Based on golden tests: "คุณสมบูรณ์ ..."
name_full = "คุณสมบูรณ์"
print(f"Lookup '{name_full}':")
hits = lookup_phones(name_full, records)
for h in hits:
    print(f"- {h['name']} {h['phones']}")
