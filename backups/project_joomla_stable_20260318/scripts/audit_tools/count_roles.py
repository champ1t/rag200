import json
from collections import Counter

data = []
with open("data/records/positions.jsonl", "r") as f:
    for line in f:
        data.append(json.loads(line))

roles = [r.get("role") for r in data if r.get("role")]
unique_roles = set(roles)

print(f"Total Records: {len(data)}")
print(f"Unique Roles: {len(unique_roles)}")
print("Roles:", unique_roles)

if "ผส.บลตน." in unique_roles:
    print("✅ 'ผส.บลตน.' found in roles.")
else:
    print("❌ 'ผส.บลตน.' NOT found in roles.")
