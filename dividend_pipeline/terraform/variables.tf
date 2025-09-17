variable "project_id" { 
    type = string 
}

variable "region" { 
    type = string 
    default = "us-central1" 
}


variable "raw_bucket" { 
    type = string 
    default = null 
}

variable "dlq_bucket" { 
    type = string 
    default = null 
}

variable "staging_bucket" { 
    type = string 
    default = null 
}

variable "temp_bucket" { 
    type = string 
    default = null 
}

# Path to your function source directory (relative to terraform/ folder)
variable "function_src_dir" {
  type    = string
  default = "../function_launcher"
}


locals {
raw_bucket = coalesce(var.raw_bucket, "dividends-raw-${var.project_id}")
dlq_bucket = coalesce(var.dlq_bucket, "dividends-dlq-${var.project_id}")
staging_bucket = coalesce(var.staging_bucket, "dataflow-staging-${var.project_id}")
temp_bucket = coalesce(var.temp_bucket, "dataflow-temp-${var.project_id}")
}