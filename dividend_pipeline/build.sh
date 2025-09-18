PROJECT=data-eng-d-091625
REGION=us-central1
REPO=artreg
IMAGE=${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/ingest-csv:1.0

# Build and push the container
gcloud builds submit --tag $IMAGE ./app/.