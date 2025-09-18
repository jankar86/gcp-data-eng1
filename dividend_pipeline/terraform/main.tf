locals {
  apis = [
    "run.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
    "logging.googleapis.com",
    "cloudbuild.googleapis.com"
  ]
}

resource "google_project_service" "enabled" {
  for_each = toset(local.apis)
  project  = var.project_id
  service  = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "raw" {
  name          = var.raw_bucket_name
  location      = var.location
  force_destroy = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "staging" {
  name          = var.staging_bucket_name
  location      = var.location
  force_destroy = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 30 } # auto-clean temp artifacts
    action    { type = "Delete" }
  }
}

# (optional) upload your YAML config so the service can read gs://.../config/brokers.yaml
resource "google_storage_bucket_object" "brokers_yaml" {
  count  = fileexists(var.brokers_config_path) ? 1 : 0
  name   = "config/brokers.yaml"
  bucket = google_storage_bucket.staging.name
  source = var.brokers_config_path
  content_type = "text/yaml"
}
