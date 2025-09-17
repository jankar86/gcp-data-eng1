import base64
import json
import os
import re
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


def _sanitize_job_name(stem: str) -> str:
    """
    Create a Dataflow-compatible job name:
    - only [a-z0-9-]
    - must start with a letter
    - must end with a letter or number
    - keep it under ~100 chars
    """
    s = stem.lower()
    s = s.replace("/", "-")
    s = re.sub(r"[^a-z0-9-]", "-", s)          # allow only [a-z0-9-]
    s = re.sub(r"-{2,}", "-", s).strip("-")    # collapse/trim dashes
    if not s or not s[0].isalpha():
        s = "d" + s                             # ensure starts with letter
    if not s[-1].isalnum():
        s = s.rstrip("-") or "djob"             # ensure ends alnum
    s = s[:80].rstrip("-")                      # truncate safely
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{s}-{ts}"


def entrypoint(event, context=None):
    try:
        data = base64.b64decode(event["data"]).decode("utf-8")
        msg = json.loads(data)

        bucket = msg["bucket"]
        name = msg["name"]

        # Only process .csv
        if not name.lower().endswith(".csv"):
            print(f"Skipping non-CSV: {name}")
            return

        gcs_path = f"gs://{bucket}/{name}"
        base = os.path.basename(name)
        job_name = _sanitize_job_name(f"dividends-csv-load-{base}")
        print(f"Launching Dataflow job: {job_name} for {gcs_path}")

        parameters = {
            "input": gcs_path,
            "output_table": f"{PROJECT_ID}:{BQ_DATASET}.{BQ_TABLE}",
            "bad_rows_gcs": f"gs://{DLQ_BUCKET}/bad_rows/",
            "temp_location": TEMP_LOCATION,
            "staging_location": STAGING_LOCATION,
        }

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

        resp = dataflow.projects().locations().flexTemplates().launch(
            projectId=PROJECT_ID, location=REGION, body=launch_body
        ).execute()
        print("Dataflow launch response:")
        print(json.dumps(resp, indent=2))

    except HttpError as e:
        print(f"HttpError launching Dataflow: {e}")
        try:
            print(e.content.decode() if hasattr(e, 'content') else str(e))
        except Exception:
            pass
        raise
    except Exception as e:
        print(f"Unhandled exception: {e}")
        raise
