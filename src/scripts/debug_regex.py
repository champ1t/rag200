
import re
from src.utils.extractors import is_valid_mapping_line

def test_regex():
    lines = [
        "ระนอง 100: 077001001",
        "09891Z0300:สตูล",
        "02-1234567"
    ]
    for l in lines:
        print(f"Line: '{l}' -> Valid: {is_valid_mapping_line(l)}")
        
    # Test internal regex manually
    p = r"\b0\d{1,2}[-]?\d{6,8}\b"
    print(f"Regex: {p}")
    t = "ระนอง 100: 077001001"
    m = re.search(p, t)
    print(f"Match: {m}")

if __name__ == "__main__":
    test_regex()
