# schema_dividends.py
from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Dict

CANON_COLS = [
  "row_hash","account_id","broker","broker_account","symbol","cusip","isin","security_name",
  "event_type","ex_date","record_date","pay_date","quantity","gross_amount","withholding_tax",
  "fees","net_amount","currency","reinvested","drip_price","created_ts","source_file","line_no","notes"
]

def mk_row_hash(d: Dict) -> str:
    key = f"{d.get('broker')}|{d.get('broker_account')}|{d.get('symbol')}|{d.get('pay_date')}|{d.get('net_amount')}|{d.get('source_file')}|{d.get('line_no')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
