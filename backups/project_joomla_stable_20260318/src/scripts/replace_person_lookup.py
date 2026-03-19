
def main():
    path = "src/chat_engine.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    skipping = False
    replaced = False
    
    for line in lines:
        if 'elif intent == "PERSON_LOOKUP":' in line:
            # Write new logic
            new_lines.append('        # 1.2 PERSON_LOOKUP (Roles/WhoIs)\n')
            new_lines.append('        elif intent == "PERSON_LOOKUP":\n')
            new_lines.append('             print("[DEBUG] Route: PERSON_LOOKUP")\n')
            new_lines.append('             t_start = time.time()\n')
            new_lines.append('             return self.directory_handler.handle(q)\n\n')
            skipping = True
            replaced = True
            continue
            
        if 'elif intent == "REFERENCE_LINK":' in line:
            skipping = False
            # This line marks end of skip. We include it.
            new_lines.append(line)
            continue
            
        if skipping:
            continue
            
        new_lines.append(line)
        
    if replaced:
        print("Line-by-line replacement applied.")
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    else:
        print("Target line not found.")

if __name__ == "__main__":
    main()
