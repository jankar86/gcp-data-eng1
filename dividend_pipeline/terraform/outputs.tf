output "raw_bucket" { 
    value = google_storage_bucket.raw.name 
    }

output "dlq_bucket" { 
    value = google_storage_bucket.dlq.name 
    }

output "staging_bucket" { 
    value = google_storage_bucket.staging.name 
    }

output "temp_bucket" { 
    value = google_storage_bucket.temp.name 
    }

output "pubsub_topic" { 
    value = google_pubsub_topic.gcs_raw.name 
    }

# output "function_name" { 
#     value = google_cloudfunctions2_function.launcher.name 
#     }

output "bq_table" { 
    value = "${google_bigquery_dataset.dividends.dataset_id}.${google_bigquery_table.fact_dividends.table_id}" 
    }