
import re

def test_regex():
    query = "ใครดูแลงาน FTTx"
    query_lower = query.lower()
    
    team_indicators = ["งาน", "ทีม", "กลุ่ม", "ฝ่าย", "ส่วน", "กอง"]
    
    print(f"Query Lower: '{query_lower}'")
    
    for ti in team_indicators:
        if ti in query_lower:
            pattern = fr"{ti}\s+[A-Za-z0-9ก-๙]+"
            print(f"Testing Ti: '{ti}', Pattern: '{pattern}'")
            match = re.search(pattern, query_lower)
            if match:
                print(f"✅ Match found: '{match.group(0)}'")
            else:
                print(f"❌ No match")

if __name__ == "__main__":
    test_regex()
