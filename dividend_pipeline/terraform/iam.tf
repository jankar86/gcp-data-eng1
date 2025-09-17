# terraform/main.tf (top-level, if not already present)
data "google_project" "current" {}

# Let GCS publish to the topic
resource "google_pubsub_topic_iam_member" "gcs_can_publish" {
  topic  = google_pubsub_topic.gcs_raw.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gs-project-accounts.iam.gserviceaccount.com"
}


# Service Accounts
resource "google_service_account" "dataflow_sa" {
account_id = "dataflow-worker-sa"
display_name = "Dataflow Worker SA"
}


resource "google_service_account" "function_sa" {
account_id = "dividends-launcher-sa"
display_name = "CFn2 Launcher SA"
}

# IAM for SA
resource "google_project_iam_member" "dataflow_roles" {
for_each = toset([
"roles/dataflow.worker",
"roles/dataflow.developer",
"roles/storage.objectAdmin",
"roles/bigquery.dataEditor",
"roles/bigquery.jobUser"
])
project = var.project_id
role = each.value
member = "serviceAccount:${google_service_account.dataflow_sa.email}"
}


resource "google_project_iam_member" "function_roles" {
for_each = toset([
"roles/dataflow.developer",
"roles/storage.objectViewer",
"roles/pubsub.subscriber",
"roles/run.invoker",
"roles/iam.serviceAccountUser"
])
project = var.project_id
role = each.value
member = "serviceAccount:${google_service_account.function_sa.email}"
}