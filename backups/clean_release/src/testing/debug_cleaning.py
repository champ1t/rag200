
import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from rag.article_cleaner import clean_article_content, strip_menus

file_path = "data/processed/INTERNAL_SMC_IP_smc_index.php_option_com_content_view_article_id_670_huawei-bras-ippgw-command_catid_49_-smc_Itemid_84.json"

with open(file_path, 'r') as f:
    data = json.load(f)

text = data['text']
print(f"Original Length: {len(text)}")

# Step 1: Clean
cleaned = clean_article_content(text, keep_metadata=True)
print(f"After clean_article_content: {len(cleaned)}")

# Step 2: Strip Menus
stripped = strip_menus(cleaned)
print(f"After strip_menus: {len(stripped)}")

print("-" * 20)
print("FINAL CONTENT:")
print(stripped)
print("-" * 20)

# Check for keywords
keywords = ["recycle", "lock", "display ip pool"]
for kw in keywords:
    if kw in stripped:
        print(f"Keyword '{kw}' FOUND")
    else:
        print(f"Keyword '{kw}' MISSING")
