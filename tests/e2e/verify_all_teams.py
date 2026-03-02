import yaml
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.chat_engine import ChatEngine

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_teams(path: str):
    teams = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                teams.append(json.loads(line))
    return teams

def verify_all_teams():
    print("=== Bulk Verifying Team Contacts (Phase 222) ===")
    
    cfg = load_config("configs/config.yaml")
    engine = ChatEngine(cfg)
    
    teams = load_teams("data/records/teams.jsonl")
    print(f"[INFO] Found {len(teams)} teams.")
    
    results = []
    
    for t in teams:
        team_name = t.get("team")
        if not team_name: continue
        
        query = f"ขอเบอร์ {team_name}"
        print(f"\n[TEST] Testing: {team_name} -> Query: '{query}'")
        
        # Reset context to ensure clean state
        engine.reset_context() 
        
        res = engine.process(query)
        answer = res.get("answer", "")
        route = res.get("route", "unknown")
        
        # Criteria
        status = "FAIL"
        note = ""
        
        # Check for HIT format or AMBIGUOUS (Menu)
        # Fix: Ensure we don't match the error message "ไม่พบข้อมูลเบอร์โทรศัพท์"
        is_error_msg = "ไม่พบข้อมูล" in answer and "คำแนะนำ" in answer
        
        if ("เบอร์โทร" in answer or "โทร:" in answer) and not is_error_msg:
             status = "PASS"
             note = "Hit found"
        elif "ใกล้เคียงกันหลายรายการ" in answer:
             status = "PASS (Ambiguous)"
             note = "System asked for clarification"
        elif "Case MISS" in answer: 
             status = "MISS"
             note = "Strict Miss Format"
        else:
             # Check for fallback
             if "คำแนะนำ" in answer:
                 status = "MISS (Guidance)"
                 note = "Miss with guidance"
        
        print(f"Answer Preview: {answer[:150].replace(chr(10), ' ')}...")
        print(f"[RESULT] {status} | Route: {route}")
        
        results.append({
            "team": team_name,
            "status": status,
            "note": note,
            "route": route,
            "answer_snippet": answer[:100].replace("\n", " ")
        })

    # Generate Report
    report_lines = ["# Bulk Team Contact Verification Results", "", "| Team | Status | Route | Note |", "|---|---|---|---|"]
    for r in results:
        report_lines.append(f"| {r['team']} | {r['status']} | {r['route']} | {r['note']} |")
        
    report_path = "contact_verification_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"\n[INFO] Report saved to {report_path}")

if __name__ == "__main__":
    verify_all_teams()
