import re
import hashlib
import pandas as pd
import pyarrow as pa


# ---------- Helpers ----------
def make_row_hash(row: dict) -> str:
    """
    Deterministic hash for dedupe.
    Combines broker_account, symbol, TransactionDate, Amount, and source_file.
    """
    key = f"{row.get('broker_account','')}|{row.get('Symbol','')}|{row.get('TransactionDate','')}|{row.get('Amount','')}|{row.get('source_file','')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_account_number(path: str) -> str:
    """
    Scan first few lines for 'For Account:' and extract the account number.
    Example: 'For Account: #####9153' → '9153'
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f.readlines()[:10]:
            if "For Account:" in line:
                match = re.search(r"For Account:\s*#+(\d+)", line)
                if match:
                    return match.group(1)
    return ""


# ---------- Normalization ----------
def normalize_csv(path: str, source_file: str = None) -> pa.Table:
    """
    Normalize an E*TRADE dividend CSV into a canonical Arrow Table
    with TransactionDate stored as DATE (date32[day]).
    """

    broker_account = extract_account_number(path)
    raw = pd.read_csv(path, dtype=str, skip_blank_lines=True).fillna("")

    df = pd.DataFrame()

    def col(name):
        return raw[name] if name in raw.columns else pd.Series([None] * len(raw))

    # Core fields
    df["TransactionType"] = col("TransactionType")
    df["SecurityType"] = col("SecurityType")
    df["Symbol"] = col("Symbol")
    df["Description"] = col("Description")
    df["Quantity"] = pd.to_numeric(col("Quantity"), errors="coerce")
    df["Amount"] = pd.to_numeric(col("Amount"), errors="coerce")
    df["Price"] = pd.to_numeric(col("Price"), errors="coerce")
    df["Commission"] = pd.to_numeric(col("Commission"), errors="coerce")

    # Dates → explicitly convert to date objects
    dates = pd.to_datetime(col("TransactionDate"), errors="coerce").dt.date
    date_array = pa.array(dates, type=pa.date32())

    # Provenance + hash
    df["broker_account"] = broker_account
    df["source_file"] = source_file or path
    df["created_ts"] = pd.Timestamp.utcnow()
    df["row_hash"] = df.apply(lambda r: make_row_hash(r.to_dict()), axis=1)

    # Build Arrow arrays column-by-column
    arrays = {
        "row_hash": pa.array(df["row_hash"], type=pa.string()),
        "broker_account": pa.array(df["broker_account"], type=pa.string()),
        "TransactionDate": date_array,  # ✅ guaranteed date32
        "TransactionType": pa.array(df["TransactionType"], type=pa.string()),
        "SecurityType": pa.array(df["SecurityType"], type=pa.string()),
        "Symbol": pa.array(df["Symbol"], type=pa.string()),
        "Quantity": pa.array(df["Quantity"], type=pa.float64()),
        "Amount": pa.array(df["Amount"], type=pa.float64()),
        "Price": pa.array(df["Price"], type=pa.float64()),
        "Commission": pa.array(df["Commission"], type=pa.float64()),
        "Description": pa.array(df["Description"], type=pa.string()),
        "source_file": pa.array(df["source_file"], type=pa.string()),
        "created_ts": pa.array(df["created_ts"], type=pa.timestamp("us")),
    }

    table = pa.table(arrays)

    print(f"[NORMALIZE] Built {len(df)} rows from {path}")
    return table
