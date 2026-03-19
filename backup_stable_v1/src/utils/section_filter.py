
import re
from typing import List, Optional
from src.utils.extractors import PROVINCES, ABBREVIATIONS, SCAN_KEYS, extract_location_intent

# extract_location_intent is imported directly


def slice_markdown_section(content: str, locations: List[str]) -> str:
    """
    Slice markdown content to return only sections relevant to the locations.
    Preserves Top-Level headers if they seem global.
    """
    if not locations or not content:
        return content
        
    lines = content.split('\n')
    output_lines = []
    
    # 1. Keep Global Header (first few lines) until first specific section?
    # Heuristic: Keep lines until we hit a location header
    
    # Identify location headers
    # A header is "## Location" or "1. Location" or bold "**Location**" containing the location name
    
    # Simple Logic:
    # - Scan for start of a "Location Block"
    # - A block starts when we see the location name in a significant line (Header/ListItem)
    # - A block ends when we see ANOTHER location name from our known PROVINCE list
    
    # But RAG content might be numbered list:
    # 1. Songkhla
    #    - Detail
    # 2. Phuket
    #    - Detail
    
    in_target_block = False
    keep_global_header = True
    
    for line in lines:
        line_clean = line.strip()
        # print(f"DEBUG Line: {line_clean}")
        if not output_lines or keep_global_header:
            # Check if this line starts a NON-target location block
            is_start_location = any(key in line.lower() for key in SCAN_KEYS)
            
            is_target_location = False
            for key in SCAN_KEYS:
                if key in line.lower():
                     full = ABBREVIATIONS.get(key, key)
                     if full in locations:
                         is_target_location = True
                         break
            
            # print(f"  Start={is_start_location}, Target={is_target_location}, Glob={keep_global_header}")
            
            if is_start_location:
                keep_global_header = False # Stop global mode
                if is_target_location:
                    in_target_block = True
                    output_lines.append(line)
                else:
                    in_target_block = False
            else:
                if keep_global_header:
                     output_lines.append(line)
        else:
            # We differ global header
            # Check if this line starts a NEW block
             is_start_location = any(key in line.lower() for key in SCAN_KEYS)
             
             is_target_location = False
             for key in SCAN_KEYS:
                if key in line.lower():
                     full = ABBREVIATIONS.get(key, key)
                     if full in locations:
                         is_target_location = True
                         break
             
             # print(f"  Start={is_start_location}, Target={is_target_location}, InBlock={in_target_block}")

             if is_start_location:
                 if is_target_location:
                     in_target_block = True
                     output_lines.append(line)
                 else:
                     in_target_block = False # Switch to other loc
             elif in_target_block:
                 output_lines.append(line)
                 
    # Verification: Did we actually capture the target?
    # We need to check if ANY alias of the requested locations is in the output
    found_any = False
    output_text = "\n".join(output_lines).lower()
    
    for key in SCAN_KEYS:
        if key in output_text:
             full = ABBREVIATIONS.get(key, key)
             if full in locations:
                 found_any = True
                 break
    
    # Logic: If we found the target header, accept it even if short (e.g. just contact info)
    # Only fallback if valid target NOT found, OR (Found but extremely short empty block?)
    if not found_any or (len(output_lines) < 2 and found_any): 
        # Fallback: Scan what regions ARE available in the text
        available_regions = []
        for key in SCAN_KEYS:
             if key in content.lower():
                 full_name = ABBREVIATIONS.get(key, key)
                 if full_name not in available_regions:
                     available_regions.append(full_name)
        
        if available_regions:
            # Construct helpful message (Phase 36 enhancement)
            req_str = ", ".join(locations)
            avail_str = ", ".join(sorted(available_regions))
            
            # If we found other regions but not target, helpful message is good.
            # But if we found NOTHING (e.g. no regions at all), maybe just return content.
            return f"ไม่พบข้อมูลเฉพาะสำหรับจังหวัด **{req_str}** ในบทความนี้\n\n(ข้อมูลที่มีในบทความ: {avail_str})\n\nคุณอาจลองดูข้อมูลรวมด้านล่าง:\n\n{content}"
        else:
            return content # Return original if no structure found at all

    return "\n".join(output_lines)
