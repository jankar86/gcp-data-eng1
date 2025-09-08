output "bucket_name" {
  value = google_storage_bucket.raw_data.name
}

output "dataset_id" {
  value = google_bigquery_dataset.lab_dataset.dataset_id
}

output "pubsub_topic" {
  value = google_pubsub_topic.events.name
}
