#!/usr/bin/env python3
"""
Script to insert QueryNormalizer retry logic into DirectoryHandler
"""

file_path = "/Users/jakkapatmac/Documents/NT/RAG/rag_web/src/rag/handlers/directory_handler.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Normalization retry code to insert
retry_code = """              # Phase 2.1: Query Normalizer Retry (on first miss only)
              if retry_count == 0 and self.query_normalizer:
                  print(f"[DEBUG] Team Miss. Triggering QueryNormalizer...")
                  norm_result = self.query_normalizer.normalize(query, trigger_reason="team_miss")
                  
                  if norm_result["changed"] and norm_result["confidence"] > 0.5:
                      normalized_query = norm_result["normalized_query"]
                      print(f"[QueryNormalizer] Retrying with: '{normalized_query}'")
                      
                      # Retry with normalized query (increment retry_count to prevent loop)
                      return self.handle_team_lookup(normalized_query, is_asset=is_asset, retry_count=retry_count + 1)
              
"""

# Insert at line 603 (before first team_miss return)
insert_line_1 = 602  # 0-indexed, so line 603 is index 602
lines.insert(insert_line_1, retry_code)

# Find the second team_miss return (it's now shifted by the number of lines we inserted)
shift = len(retry_code.split('\n'))
# The second one was at line 641, now it's at 641 + shift - 1
insert_line_2 = 640 + shift  # Adjusted for the first insertion

# Insert at the second location
retry_code_2 = retry_code.replace("team_miss", "team_miss_no_suggestions")
lines.insert(insert_line_2, retry_code_2)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Inserted QueryNormalizer retry logic at 2 locations")
print(f"  - Line {insert_line_1 + 1}")
print(f"  - Line {insert_line_2 + 1}")
