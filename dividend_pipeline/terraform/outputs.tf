output "raw_bucket"     { 
    value = google_storage_bucket.raw.name 
}

output "staging_bucket" { 
    value = google_storage_bucket.staging.name 
}

output "run_service_url" {
  value = google_cloud_run_v2_service.ingest.uri
}

output "dataset" { 
    value = google_bigquery_dataset.finance.dataset_id 
}

output "table"   { 
    value = google_bigquery_table.dividends_fact.table_id 
}
