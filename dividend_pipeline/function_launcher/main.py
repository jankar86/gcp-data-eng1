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

def entrypoint(event, context=None):
    data = base64.b64decode(event["data"]).decode("utf-8")
    msg = json.loads(data)

    bucket = msg["bucket"]
    name = msg["name"]

    # Only process .csv
    if not name.lower().endswith(".csv"):
        print(f"Skipping non-CSV: {name}")
        return

    gcs_path = f"gs://{bucket}/{name}"
    job_name = ("dividends-csv-load-" + name.replace("/", "-")[:50]).lower()

    print(f"Launching Dataflow job for {gcs_path}")

    parameters = {
        "input": gcs_path,
        "output_table": f"{PROJECT_ID}:{BQ_DATASET}.{BQ_TABLE}",
        "bad_rows_gcs": f"gs://{DLQ_BUCKET}/bad_rows/",
        "temp_location": TEMP_LOCATION,
        "staging_location": STAGING_LOCATION,
    }

    # Build Dataflow client
    dataflow = build("dataflow", "v1b3", cache_discovery=False)

    launch_body = {
        "launchParameter": {
            "jobName": job_name,
            "containerSpecGcsPath": FLEX_TEMPLATE_GCS_PATH,
            "parameters": parameters,
            "environment": {
                "serviceAccountEmail": WORKER_SA,
                "maxWorkers": 5,
                "tempLocation": TEMP_LOCATION,
                "workerRegion": REGION,
            },
        }
    }

    req = dataflow.projects().locations().flexTemplates().launch(
        projectId=PROJECT_ID, location=REGION, body=launch_body
    )
    resp = req.execute()
    print(json.dumps(resp, indent=2))