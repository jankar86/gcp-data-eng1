variable "project_id" { 
    type = string 
}

variable "region" { 
    type = string 
    default = "us-central1" 
}

variable "location"   { 
    type = string  
    default = "US" 
} # BigQuery location

variable "dataset_id" { 
    type = string 
    default = "finance" 
}

# Path to your brokers.yaml to upload next to the service (optional convenience)
variable "brokers_config_path" {
  type        = string
  default     = "./config/brokers.yaml"
  description = "Local file path. If present, it's uploaded to the staging bucket at config/brokers.yaml"
}

variable "raw_bucket_name" { 
    type = string 
    default = null 
}

variable "staging_bucket_name" { 
    type = string 
    default = null 
}

# Your already-pushed image (see build/push commands at bottom)
variable "container_image" {
  type = string
  # e.g. "us-central1-docker.pkg.dev/PROJECT/div/ingest-csv:1.0"
}
