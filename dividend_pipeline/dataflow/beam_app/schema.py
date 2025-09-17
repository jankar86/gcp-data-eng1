from typing import Dict


BQ_SCHEMA = {
"fields": [
{"name": "source_filename", "type": "STRING", "mode": "REQUIRED"},
{"name": "load_ts", "type": "TIMESTAMP", "mode": "REQUIRED"},
{"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
{"name": "ticker", "type": "STRING", "mode": "REQUIRED"},
{"name": "ex_date", "type": "DATE", "mode": "NULLABLE"},
{"name": "pay_date", "type": "DATE", "mode": "REQUIRED"},
{"name": "amount", "type": "NUMERIC", "mode": "REQUIRED"},
{"name": "currency", "type": "STRING", "mode": "NULLABLE"},
{"name": "shares", "type": "NUMERIC", "mode": "NULLABLE"},
{"name": "broker", "type": "STRING", "mode": "NULLABLE"},
{"name": "notes", "type": "STRING", "mode": "NULLABLE"}
]
}