# Adjust if your deployer is different
locals {
  deployer_sa_email = "tf-deployer@${var.project_id}.iam.gserviceaccount.com"
  deployer_member   = "serviceAccount:${local.deployer_sa_email}"
}

# ✅ Allow the deployer to "actAs" the function's runtime SA
resource "google_service_account_iam_member" "deployer_can_act_as_fn_sa" {
  service_account_id = google_service_account.fn_ingest_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.deployer_member
}

# resource "google_service_account_iam_member" "deployer_can_act_as_compute" {
#   service_account_id = "684902872592-compute@developer.gserviceaccount.com"
#   role               = "roles/iam.serviceAccountUser"
#   member             =  local.deployer_member
# }
