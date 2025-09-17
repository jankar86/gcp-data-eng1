import base64
import json
import os
from googleapiclient.discovery import build


# Env vars
PROJECT_ID = os.environ["PROJECT_ID"]
REGION = os.environ.get("DATAFLOW_REGION", "us-central1")
FLEX_TEMPLATE_GCS_PATH = os.environ["FLEX_TEMPLATE_GCS_PATH"]
TEMP_LOCATION = os.environ["DATAFLOW_TEMP_LOCATION"]
STAGING_LOCATION = os.environ["DATAFLOW_STAGING_LOCATION"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_TABLE = os.environ["BQ_TABLE"]
DLQ_BUCKET = os.environ["DLQ_BUCKET"]
WORKER_SA = os.environ["WORKER_SA"]


# Cloud Function Gen2 entrypoint
# Trigger: Pub/Sub (GCS notification)
