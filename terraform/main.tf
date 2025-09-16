# Enable core APIs
resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "dataflow.googleapis.com",
    "composer.googleapis.com",
    "cloudfunctions.googleapis.com"
  ])
  project = var.project_id
  service = each.key
}

# Storage bucket for raw data
resource "google_storage_bucket" "raw_data" {
  project                     = var.project_id
  name                        = "${var.project_id}-raw-data"
  location                    = var.region
  uniform_bucket_level_access = true
}

# BigQuery dataset
resource "google_bigquery_dataset" "lab_dataset" {
  dataset_id = "lab_dataset"
  project    = var.project_id
  location   = var.region
}

# Pub/Sub topic
resource "google_pubsub_topic" "events" {
  name    = "lab-events"
  project = var.project_id
}
