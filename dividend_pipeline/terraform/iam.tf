resource "google_service_account" "ingest" {
  account_id   = "div-ingest"
  display_name = "Dividend CSV Ingest"
}

# Storage access: raw read, staging read/write
resource "google_storage_bucket_iam_member" "raw_reader" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_storage_bucket_iam_member" "staging_writer" {
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingest.email}"
}

# BigQuery: write rows + run load jobs
resource "google_project_iam_member" "bq_jobuser" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_bigquery_dataset_iam_member" "bq_editor" {
  dataset_id = google_bigquery_dataset.finance.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingest.email}"
}

# Eventarc delivery SA must invoke Cloud Run
resource "google_service_account" "eventarc" {
  account_id   = "div-eventarc"
  display_name = "Eventarc Trigger SA"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}
