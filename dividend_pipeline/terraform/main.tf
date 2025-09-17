# Enable required services
resource "google_project_service" "apis" {
for_each = toset([
"compute.googleapis.com",
"storage.googleapis.com",
"bigquery.googleapis.com",
"pubsub.googleapis.com",
"dataflow.googleapis.com",
"eventarc.googleapis.com",
"run.googleapis.com",
"cloudfunctions.googleapis.com",
"cloudbuild.googleapis.com"
])
service = each.key
}


# Buckets
resource "google_storage_bucket" "raw" {
name = local.raw_bucket
location = var.region
uniform_bucket_level_access = true
force_destroy = true
}


resource "google_storage_bucket" "dlq" {
name = local.dlq_bucket
location = var.region
uniform_bucket_level_access = true
force_destroy = true
}


resource "google_storage_bucket" "staging" {
name = local.staging_bucket
location = var.region
uniform_bucket_level_access = true
force_destroy = true
}


resource "google_storage_bucket" "temp" {
name = local.temp_bucket
location = var.region
uniform_bucket_level_access = true
force_destroy = true
}


# Pub/Sub notification from GCS (object finalize)
resource "google_pubsub_topic" "gcs_raw" {
name = "gcs.dividends.raw"
}


resource "google_storage_notification" "raw_finalize" {
bucket = google_storage_bucket.raw.name
payload_format = "JSON_API_V1"
topic = google_pubsub_topic.gcs_raw.id
event_types = ["OBJECT_FINALIZE"]
}


# BigQuery dataset + table
resource "google_bigquery_dataset" "dividends" {
dataset_id = "dividends"
location = "US"
delete_contents_on_destroy = true
}


resource "google_bigquery_table" "fact_dividends" {
dataset_id = google_bigquery_dataset.dividends.dataset_id
table_id = "fact_dividends"
deletion_protection = false
schema = jsonencode([
{"name":"source_filename","type":"STRING","mode":"REQUIRED"},
{"name":"load_ts","type":"TIMESTAMP","mode":"REQUIRED"},
{"name":"account_id","type":"STRING","mode":"REQUIRED"},
{"name":"ticker","type":"STRING","mode":"REQUIRED"},
{"name":"ex_date","type":"DATE","mode":"NULLABLE"},
{"name":"pay_date","type":"DATE","mode":"REQUIRED"},
{"name":"amount","type":"NUMERIC","mode":"REQUIRED"},
{"name":"currency","type":"STRING","mode":"NULLABLE"},
{"name":"shares","type":"NUMERIC","mode":"NULLABLE"},
{"name":"broker","type":"STRING","mode":"NULLABLE"},
{"name":"notes","type":"STRING","mode":"NULLABLE"}
])
}
