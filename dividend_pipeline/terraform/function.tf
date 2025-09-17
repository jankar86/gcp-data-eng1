# Zip the function source from your repo
# Excludes common noise; tweak as needed
data "archive_file" "function_src" {
  type        = "zip"
  source_dir  = var.function_src_dir
  output_path = "${path.module}/.build/function_launcher.zip"

  excludes = [
    ".git", ".gitignore", ".venv", "__pycache__", ".DS_Store",
    "node_modules", "*.pyc"
  ]
}

# Upload the zip to the staging bucket with a content-addressed name
# Changing code -> new md5 -> new object name -> function rebuild
resource "google_storage_bucket_object" "function_src" {
  name         = "function_src/function-${data.archive_file.function_src.output_md5}.zip"
  bucket       = google_storage_bucket.staging.name
  source       = data.archive_file.function_src.output_path
  content_type = "application/zip"
}

# (PATCH) Cloud Function uses the uploaded object as source
# Replace the existing google_cloudfunctions2_function.launcher build_config.source with this:
resource "google_cloudfunctions2_function" "launcher" {
  name        = "dividends-flex-launcher"
  location    = var.region
  description = "Launch Dataflow Flex on GCS finalize"

  build_config {
    runtime     = "python311"
    entry_point = "entrypoint"

    source {
      storage_source {
        bucket = google_storage_bucket.staging.name
        object = google_storage_bucket_object.function_src.name
      }
    }
  }

  service_config {
    max_instance_count    = 3
    available_memory      = "512M"
    timeout_seconds       = 540
    service_account_email = google_service_account.function_sa.email
    environment_variables = {
      FLEX_TEMPLATE_GCS_PATH   = "gs://${google_storage_bucket.staging.name}/flex_templates/dividends_spec.json"
      DATAFLOW_TEMP_LOCATION   = "gs://${google_storage_bucket.temp.name}/temp"
      DATAFLOW_STAGING_LOCATION= "gs://${google_storage_bucket.staging.name}/staging"
      DATAFLOW_REGION          = var.region
      BQ_DATASET               = google_bigquery_dataset.dividends.dataset_id
      BQ_TABLE                 = google_bigquery_table.fact_dividends.table_id
      DLQ_BUCKET               = google_storage_bucket.dlq.name
      WORKER_SA                = google_service_account.dataflow_sa.email
      PROJECT_ID               = var.project_id
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.gcs_raw.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  # Rebuild if the uploaded source object changes (content hash)
  lifecycle {
    replace_triggered_by = [google_storage_bucket_object.function_src]
  }

  depends_on = [
    google_pubsub_topic_iam_member.gcs_can_publish
  ]
}