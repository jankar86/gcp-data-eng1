import re

def extract_account_number(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f.readlines()[:10], start=1):
            print(f"[LINE {i}] {line.strip()}")
            if "account" in line.lower():
                match = re.search(r"For\s*Account[:\s,]*([#\d]+)", line, flags=re.IGNORECASE)
                if match:
                    acct = match.group(1).lstrip("#")
                    print(f"[MATCHED] Extracted account: {acct}")
                    return acct
    print("[NO MATCH FOUND]")
    return ""

if __name__ == "__main__":
    acct = extract_account_number("etrade-9153-7-3-24_6-5-25.csv")
    print(f"Final result: {acct}")