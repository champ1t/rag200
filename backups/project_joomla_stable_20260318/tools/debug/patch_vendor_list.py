#!/usr/bin/env python3
"""
Manual patch script to update vendor list generation.
Replaces category grouping with global numeric selection.
"""

import re

file_path = '/Users/jakkapatmac/Documents/NT/RAG/rag_web/src/chat_engine.py'

# Read file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the old code block (category grouping)
old_code = '''                         # Group by Category (Preserving Order from Ranked List)
                          groups = {}
                          for art in vendor_articles:
                              cat = art.get('category', 'ทั่วไป')
                              if cat not in groups:
                                  groups[cat] = []
                              groups[cat].append(art['title'])
                          
                          # Format Output
                          options_text = ""
                          for cat, titles in groups.items():
                              options_text += f"\\n[{cat}]\\n"
                              for t in titles:
                                  options_text += f"• {t}\\n"'''

# Define the new code (numeric session)
new_code = '''                         # ============================================================
                          # NUMERIC SELECTION: Global numbering (NO category reset)
                          # ============================================================
                          items = []
                          for art in vendor_articles:
                              items.append({
                                  "url": art['url'],
                                  "title": art['title'],
                                  "category": art.get('category', '')
                              })
                          
                          # Create session with global numbering
                          session = self.numeric_selection_resolver.create_session(
                              items, context="article_selection",
                              prompt_text=f"กรุณาเลือกหมายเลข (1-{len(items)})"
                          )
                          options_text = self.numeric_selection_resolver.format_numbered_list(
                              session['items'], context="article_selection"
                          )
                          self.pending_numeric_session = session'''

# Replace
if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ Replaced category grouping with numeric session")
else:
    print("❌ Old code not found - trying line-by-line match")
    exit(1)

# Also update the answer format
old_answer = '''                                  f"พบเอกสารที่เกี่ยวข้องในระบบ SMC ดังนี้:\\n"
                                  f"{options_text}\\n"
                                  f"กรุณาเลือกหัวข้อที่ต้องการ"'''

new_answer = '''                                  f"พบ {len(vendor_articles)} เอกสารที่เกี่ยวข้อง:\\n\\n"
                                  f"{options_text}\\n\\n"
                                  f"{session['prompt_text']}"'''

if old_answer in content:
    content = content.replace(old_answer, new_answer)
    print("✅ Updated answer format")
else:
    print("⚠️  Answer format not found (may already be updated)")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ File updated: {file_path}")
print("\n📝 Changes made:")
print("  1. Replaced category grouping (lines 2214-2227)")
print("  2. Added numeric session creation")
print("  3. Updated answer format (lines 2231-2233)")
print("\n🧪 Test: python3 -m src.main chat")
print("     Query: คำสั่ง huawei")
print("     Expected: Global numbered list (1-10)")
