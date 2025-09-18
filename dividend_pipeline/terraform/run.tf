resource "google_cloud_run_v2_service" "ingest" {
  name     = "div-csv-ingest"
  deletion_protection=false
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" # or "INGRESS_TRAFFIC_ALL" if you want public
  template {
    service_account = google_service_account.ingest.email
    containers {
      image = var.container_image
      env {
        name  = "STAGING_BUCKET"
        value = google_storage_bucket.staging.name
      }
      # Prefer config from GCS path; your service should read brokers.yaml from this gs:// URI.
      env {
        name  = "CONFIG_PATH"
        value = "gs://${google_storage_bucket.staging.name}/config/brokers.yaml"
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      # Optional memory/CPU
      resources {
        limits = {
          "memory" = "1Gi"
          "cpu"    = "1"
        }
      }
    }
  }
  depends_on = [google_project_service.enabled]
}

# Allow unauthenticated only if you need it; Eventarc uses its own SA to invoke.
resource "google_cloud_run_service_iam_member" "allow_eventarc_invoke" {
  location = google_cloud_run_v2_service.ingest.location
  service  = google_cloud_run_v2_service.ingest.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.eventarc.email}"
}

# Eventarc trigger: fires on object finalize (*.csv) in the raw bucket
resource "google_eventarc_trigger" "gcs_to_run" {
  name     = "div-csv-finalize"
  location = var.region

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.raw.name
  }

  # Optional suffix filter implemented via event filters (newer provider versions support "subject" matching).
  # If your provider doesn't support "filters" on subject, just filter inside your code.
  # For broad compatibility, we pass everything and let the service ignore non-CSV.

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.ingest.name
      region  = var.region
      path    = "/"
    }
  }

  service_account = google_service_account.eventarc.email

  depends_on = [
    google_cloud_run_v2_service.ingest,
    google_storage_bucket.raw
  ]
}
