#!/usr/bin/env bash
set -euo pipefail

# --- EDIT THESE ---
PROJECT_ID="data-eng-d"
REGION="us-central1"
REPO_NAME="gcp-data-eng1"   # just used for names
# Replace YOUR_EMAIL below with the Google identity you 'gcloud auth login' with.
YOUR_EMAIL=""

# --- Derived ---
TF_STATE_BUCKET="${PROJECT_ID}-tf-state"
SA_ID="tf-deployer"
SA_EMAIL="${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Enabling required APIs..."
gcloud services enable storage.googleapis.com iam.googleapis.com serviceusage.googleapis.com --project "$PROJECT_ID"

echo "Creating Terraform state bucket: gs://$TF_STATE_BUCKET ..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${TF_STATE_BUCKET}" || true
# Hardening & safety:
gsutil versioning set on "gs://${TF_STATE_BUCKET}"
gsutil retention set 7d "gs://${TF_STATE_BUCKET}"              # optional retention
gsutil pap set enforced "gs://${TF_STATE_BUCKET}"              # public access prevention
gsutil uniformbucketlevelaccess set on "gs://${TF_STATE_BUCKET}"

echo "Creating deploy Service Account..."
gcloud iam service-accounts create "$SA_ID" \
  --project "$PROJECT_ID" \
  --display-name "Terraform Deployer (local impersonation)" || true

echo "Granting least-privilege roles (adjust as needed for your TF code)..."
# Allow enabling services
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/serviceusage.serviceUsageAdmin"

# Allow managing bucket objects IN THE STATE BUCKET ONLY
gsutil iam ch "serviceAccount:${SA_EMAIL}:objectAdmin" "gs://${TF_STATE_BUCKET}"

# GCS / BigQuery / PubSub admin for Week1 resources (tighten later if you prefer)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/storage.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/bigquery.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/pubsub.admin"

echo "Allow YOUR USER to impersonate the deployer SA..."

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project "$PROJECT_ID" \
  --member "user:${YOUR_EMAIL}" \
  --role "roles/iam.serviceAccountTokenCreator"

echo "Bootstrap complete."
echo "State bucket: gs://${TF_STATE_BUCKET}"
echo "Deployer SA:  ${SA_EMAIL}"
