locals {
  fn_name         = "ingest-csv-to-bq"
  fn_region       = var.region
  raw_bucket_name = "${var.project_id}-raw-data"
  dataset_id      = google_bigquery_dataset.lab_dataset.dataset_id
}

# Service account for the function (least-privileged)
resource "google_service_account" "fn_ingest_sa" {
  account_id   = "fn-ingest-csv"
  display_name = "Fn SA: Ingest CSV to BigQuery"
}

# Permissions: read objects, load to BigQuery
resource "google_project_iam_member" "fn_sa_storage_obj_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.fn_ingest_sa.email}"
}

resource "google_project_iam_member" "fn_sa_bq_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.fn_ingest_sa.email}"
}

resource "google_project_iam_member" "fn_sa_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.fn_ingest_sa.email}"
}

# Allow Eventarc to invoke the function
resource "google_project_iam_member" "eventarc_receive" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.fn_ingest_sa.email}"
}

# Zip the function source from local folder (simple, works for small labs)
data "archive_file" "fn_source" {
  type        = "zip"
  output_path = "${path.module}/../build/ingest_csv.zip"
  source_dir  = "${path.module}/../functions/ingest_csv"
}

# A bucket to stage the function source (reuse state bucket or make a small code bucket)
resource "google_storage_bucket" "code_bucket" {
  name                        = "${var.project_id}-fn-code"
  location                    = var.region
  uniform_bucket_level_access = true
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 7 }
  }
}

resource "google_storage_bucket_object" "fn_zip" {
  name   = "ingest_csv_${data.archive_file.fn_source.output_md5}.zip"
  bucket = google_storage_bucket.code_bucket.name
  source = data.archive_file.fn_source.output_path
}

resource "google_cloudfunctions2_function" "ingest_csv" {
  name     = local.fn_name
  location = var.region

  build_config {
    runtime     = "python310"
    entry_point = "ingest_gcs_to_bq"
    source {
      storage_source {
        bucket = google_storage_bucket.code_bucket.name
        object = google_storage_bucket_object.fn_zip.name
      }
    }
  }

  service_config {
    service_account_email = google_service_account.fn_ingest_sa.email
    available_memory      = "512M"
    timeout_seconds       = 540
    ingress_settings      = "ALLOW_INTERNAL_ONLY" # or as needed
  }

  # <-- This creates the Eventarc trigger for GCS finalize events
  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    service_account_email = google_service_account.fn_ingest_sa.email
    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.raw_data.name
    }
  }
}
