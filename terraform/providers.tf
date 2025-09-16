provider "google" {
  project = var.project_id
  region  = var.region
  # Option A: pick up from env var GOOGLE_IMPERSONATE_SERVICE_ACCOUNT (recommended)
  # Option B: uncomment next line to hardcode:
  #impersonate_service_account   = "tf-deployer@${var.project_id}.iam.gserviceaccount.com"
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  #impersonate_service_account = "tf-deployer@${var.project_id}.iam.gserviceaccount.com"
}
