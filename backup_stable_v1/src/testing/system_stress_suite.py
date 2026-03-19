
import sys
import os
import yaml
import time
from typing import List, Dict

# Add project root
sys.path.append(os.getcwd())

from src.chat_engine import ChatEngine
from src.main import load_config

# 5 Categories x 10 Cases (50 Total)
TEST_CASES = {
    "CONTACT": [
        "เบอร์ ชจญ.", "เบอร์ ภูเก็ต", "เบอร์ งาน smc", "ติดต่อคุณสมชาย", "เบอร์ ip network",
        "เบอร์ ผส.พส.", "เบอร์ noc", "เบอร์ แผนกจัดซื้อ", "เบอร์ คุณวิชัย", "ติดต่อ helpdesk"
    ],
    "PERSON": [
        "คุณสมชาย", "ผจก ภ.4 คือใคร", "ค้นหา สมชาย", "ผู้จัดการ ขอนแก่น", "รายชื่อคนในงาน smc",
        "นายสมศักดิ์", "ผส.พส. คือใคร", "คุณวิชัย อยู่ที่ไหน", "คนชื่อ สมพร", "หัวหน้างาน noc"
    ],
    "TEAM": [
        "งาน smc", "สมาชิก helpdesk", "คนในทีม noc", "หน้าที่ งาน csoc", "งาน support",
        "ทีม develop", "ฝ่ายขาย", "งาน network", "สมาชิก ทีม ip", "คนใน แผนกบัญชี"
    ],
    "TYPE A (PROCEDURE)": [
        "วิธี reset password email", "ตั้งค่า onu zte", "command huawei", "คู่มือ vpn", "ขั้นตอนเบิกของ",
        "วิธีแก้เน็ตช้า", "config router cisco", "manual mikrotik", "ขั้นตอนลาป่วย", "วิธีใช้ edoc"
    ],
    "TYPE B (TUTORIAL)": [
        "ทำความรู้จัก EtherChannel", "concept ospf", "อธิบาย vlan", "หลักการ bgp", "what is mpls",
        "concept sd-wan", "อธิบาย firewall", "หลักการทำงาน dhcp", "nat คืออะไร", "overview 5g"
    ]
}

def run_system_stress_test():
    print("=== Phase 128: System-Wide Stress Test (10x5) ===")
    config_path = os.path.join(os.getcwd(), "configs/config.yaml")
    cfg = load_config(config_path)
    chat = ChatEngine(cfg)
    
    results = {}
    report_lines = []
    report_lines.append("# System Stress Test Report (Phase 128)")
    report_lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    total_latency = 0
    count_queries = 0

    for category, queries in TEST_CASES.items():
        print(f"\n--- Testing Category: {category} ---")
        report_lines.append(f"## Category: {category}")
        report_lines.append("| Query | Status | Latency (s) | Notes |")
        report_lines.append("|---|---|---|---|")
        
        category_results = []
        for q in queries:
            print(f"> Query: {q}")
            t0 = time.time()
            try:
                # ChatEngine.process(self, input_text)
                response = chat.process(q)
                
                # Handle Dict response (e.g. from structured handlers)
                if isinstance(response, dict):
                     # Try to get 'text' or 'answer', otherwise dump json
                     response_text = response.get('answer') or response.get('text') or str(response)
                     # Check if it has 'content' or similar? assuming str dump for now or specific keys if known.
                     # Actually most handlers return string, but if ContactHandler returns dict...
                else:
                     response_text = str(response) if response else ""

                latency = time.time() - t0
                total_latency += latency
                count_queries += 1
                
                # Validation Logic
                status = "PASS"
                notes = ""
                
                if not response_text or "ขออภัย" in response_text:
                    status = "FAIL"
                    notes = "Refusal/Empty"
                elif category == "TYPE B (TUTORIAL)":
                    if "Structured Fast-Path" in response_text: 
                         status = "FAIL" 
                         notes = "Fast-Path Leak"
                    elif "ไม่พบข้อมูล" in response_text and len(response_text) < 100:
                         status = "WARN"
                         notes = "Low Content"

                # Check for Latency Target (< 5s for most, < 10s for tutorials)
                if latency > 8.0:
                    status = "SLOW" if status == "PASS" else status
                
                res_snippet = response_text[:50].replace('\n', ' ') if response_text else "None"
                print(f"  [Latency: {latency:.2f}s] {status} - {res_snippet}...")
                
                report_lines.append(f"| {q} | {status} | {latency:.2f} | {notes} |")
                category_results.append({"query": q, "status": status, "latency": latency})
                
            except Exception as e:
                print(f"  [ERROR] {e}")
                report_lines.append(f"| {q} | ERROR | 0.00 | {str(e)} |")
                category_results.append({"query": q, "status": "ERROR", "latency": 0})
        
        results[category] = category_results
        report_lines.append("") # Spacer

    # Summary
    print("\n=== SYSTEM HEALTH SUMMARY ===")
    report_lines.append("## Summary")
    total = 0
    passed = 0
    
    for cat, res in results.items():
        cat_pass = sum(1 for r in res if r['status'] in ['PASS', 'SLOW']) # SLOW is technically a pass on logic
        print(f"{cat}: {cat_pass}/{len(res)} PASS")
        report_lines.append(f"- **{cat}**: {cat_pass}/{len(res)} PASS")
        total += len(res)
        passed += cat_pass
        
    avg_latency = total_latency / count_queries if count_queries > 0 else 0
    summary_text = f"Total: {passed}/{total} ({passed/total*100:.1f}%) | Avg Latency: {avg_latency:.2f}s"
    print(summary_text)
    report_lines.append(f"\n**{summary_text}**")
    
    # Write Report
    report_path = "stress_test_report_phase128.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n[INFO] Report saved to {report_path}")

if __name__ == "__main__":
    run_system_stress_test()
