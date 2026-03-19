
import json
import os

DIRECTORY_PATH = "data/records/directory.jsonl"

NEW_CONTACTS = [
    {
        "id": "manual_add_smc_001",
        "name": "นายกัปตัน (Captain)",
        "name_norm": "นายกัปตัน captain กับตัน",
        "role": "SMC Support",
        "type": "person",
        "phones": ["092-992-9459"],
        "emails": [],
        "tags": ["SMC", "HelpDesk", "Support"],
        "phone_sources": {"092-992-9459": ["Manual Entry"]}
    },
    {
        "id": "manual_add_smc_002",
        "name": "นายก้าน (Karn)",
        "name_norm": "นายก้าน karn",
        "role": "SMC Support",
        "type": "person",
        "phones": ["084-468-9122"],
        "emails": [],
        "tags": ["SMC", "HelpDesk", "Support"],
        "phone_sources": {"084-468-9122": ["Manual Entry"]}
    },
    {
        "id": "manual_add_smc_003",
        "name": "นายบอม (Bom)",
        "name_norm": "นายบอม bom",
        "role": "SMC Support",
        "type": "person",
        "phones": ["061-783-6661"],
        "emails": [],
        "tags": ["SMC", "HelpDesk", "Support"],
        "phone_sources": {"061-783-6661": ["Manual Entry"]}
    }
]

# Note: User query was "กับตัน" -> spelled "กัปตัน" or "กับตัน"?
# Query: "เบอร์คุณกับตัน" -> "กับตัน"
# I added "กับตัน" to name_norm to be safe.
# Query: "เบอร์คุณบอม" -> "บอม"
# Query: "เบอร์คุณก้าน" -> "ก้าน"

def append_contacts():
    with open(DIRECTORY_PATH, "a", encoding="utf-8") as f:
        for c in NEW_CONTACTS:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Appended {len(NEW_CONTACTS)} contacts to {DIRECTORY_PATH}")

if __name__ == "__main__":
    append_contacts()
