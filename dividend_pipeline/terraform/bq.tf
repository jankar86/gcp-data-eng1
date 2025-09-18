resource "google_bigquery_dataset" "finance" {
  dataset_id  = var.dataset_id
  location    = var.location
  delete_contents_on_destroy = true
}

# Schema is provided inline as JSON for convenience.
# You can also split this into a separate .json file and use file().
resource "google_bigquery_table" "dividends_fact" {
  dataset_id = google_bigquery_dataset.finance.dataset_id
  table_id   = "dividends_fact"

  time_partitioning {
    type  = "DAY"
    field = "pay_date"
  }

  clustering = ["account_id", "symbol"]

  schema = <<EOF
[
  {"name":"row_hash","type":"STRING","mode":"REQUIRED"},
  {"name":"account_id","type":"STRING"},
  {"name":"broker","type":"STRING"},
  {"name":"broker_account","type":"STRING"},
  {"name":"symbol","type":"STRING"},
  {"name":"cusip","type":"STRING"},
  {"name":"isin","type":"STRING"},
  {"name":"security_name","type":"STRING"},
  {"name":"event_type","type":"STRING"},
  {"name":"ex_date","type":"DATE"},
  {"name":"record_date","type":"DATE"},
  {"name":"pay_date","type":"DATE"},
  {"name":"quantity","type":"NUMERIC"},
  {"name":"gross_amount","type":"NUMERIC"},
  {"name":"withholding_tax","type":"NUMERIC"},
  {"name":"fees","type":"NUMERIC"},
  {"name":"net_amount","type":"NUMERIC"},
  {"name":"currency","type":"STRING"},
  {"name":"reinvested","type":"BOOL"},
  {"name":"drip_price","type":"NUMERIC"},
  {"name":"created_ts","type":"TIMESTAMP"},
  {"name":"source_file","type":"STRING"},
  {"name":"line_no","type":"INT64"},
  {"name":"notes","type":"STRING"}
]
EOF
}
