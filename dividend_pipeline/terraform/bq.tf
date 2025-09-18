resource "google_bigquery_dataset" "finance" {
  dataset_id  = var.dataset_id
  location    = var.location
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "etrade_dividends" {
  deletion_protection=false
  dataset_id = google_bigquery_dataset.finance.dataset_id
  table_id   = "etrade_dividends"

  # Partition on TransactionDate (payout date of dividends/transactions)
  time_partitioning {
    type  = "DAY"
    field = "TransactionDate"
  }

  # Cluster by broker_account + Symbol for query efficiency
  clustering = ["broker_account", "Symbol"]

  schema = <<EOF
[
  {"name":"row_hash","type":"STRING","mode":"NULLABLE"},
  {"name":"broker_account","type":"STRING"},
  {"name":"TransactionDate","type":"DATE"},
  {"name":"TransactionType","type":"STRING"},
  {"name":"SecurityType","type":"STRING"},
  {"name":"Symbol","type":"STRING"},
  {"name":"Quantity","type":"NUMERIC"},
  {"name":"Amount","type":"NUMERIC"},
  {"name":"Price","type":"NUMERIC"},
  {"name":"Commission","type":"NUMERIC"},
  {"name":"Description","type":"STRING"},
  {"name":"source_file","type":"STRING"},
  {"name":"created_ts","type":"TIMESTAMP"}
]
EOF
}