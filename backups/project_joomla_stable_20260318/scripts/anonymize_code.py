import os
import re

# Directory to anonymize
TARGET_DIR = "backups/clean_release"

# Sensitive patterns map: { "SENSITIVE_STRING": "PLACEHOLDER" }
# Order matters: more specific first
REPLACEMENTS = {
    "10.192.133.33": "INTERNAL_SMC_IP",
    "10.192.39.50": "INTERNAL_NMS_IP",
    "10.192.1.1": "INTERNAL_TEST_IP",
    "totsni.com": "EXTERNAL_NMS_DOMAIN",
    "intranet.ntplc.co.th": "INTRANET_DOMAIN",
    "webhr.ntplc.co.th": "HR_DOMAIN",
    "lms.ntplc.co.th": "LMS_DOMAIN",
    "mail.ntplc.co.th": "MAIL_DOMAIN",
    "ntplc.co.th": "COMPANY_DOMAIN",
    "ntplc": "COMPANY_NAME",
    "pvd.mfcfund.com": "PVD_FUND_DOMAIN",
    "192.168.99.200": "DEV_SERVER_IP",
    "vinaora.com": "VISITOR_COUNTER_DOMAIN",
}

# Also sanitize raw regex patterns that might expose IPs/Domains
# e.g. r"10\.192\.133\.33"
REGEX_REPLACEMENTS = {
    r"10\.192\.133\.33": "INTERNAL_SMC_IP",
    r"ntplc\.co\.th": "COMPANY_DOMAIN"
}

def anomyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. String Replacements
        for sensitive, placeholder in REPLACEMENTS.items():
            content = content.replace(sensitive, placeholder)
            
        # 2. Regex Replacements (if any specific pattern matches)
        for sensitive_pattern, placeholder in REGEX_REPLACEMENTS.items():
            content = re.sub(sensitive_pattern, placeholder, content)
            
        if content != original_content:
            print(f"Sanitizing: {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
    except UnicodeDecodeError:
        print(f"Skipping binary file: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    print(f"Starting anonymization on {TARGET_DIR}...")
    if not os.path.exists(TARGET_DIR):
        print(f"Target directory {TARGET_DIR} not found!")
        return

    for root, dirs, files in os.walk(TARGET_DIR):
        # Skip hidden dirs
        if "/." in root: continue
        
        for file in files:
            if file.endswith(('.py', '.md', '.json', '.yaml', '.sh', '.txt')):
                filepath = os.path.join(root, file)
                anomyze_file(filepath)
                
    print("Anonymization complete.")

if __name__ == "__main__":
    main()
