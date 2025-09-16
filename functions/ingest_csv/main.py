import os
import json
from google.cloud import bigquery, storage

PROJECT_ID = os.environ["PROJECT_ID"]
DATASET_ID = os.environ["DATASET_ID"]  # e.g., "lab_dataset"

bq = bigquery.Client(project=PROJECT_ID)
gcs = storage.Client(project=PROJECT_ID)

def _table_name_from_path(object_name: str) -> str:
    """
    Map gs://bucket/raw/<table>/<file>.csv -> table name
    e.g., raw/customers/2024-09-01.csv -> customers
    """
    parts = object_name.split("/")
    if len(parts) >= 2 and parts[0] in ("raw", "staging", "bronze"):
        return parts[1].lower().replace("-", "_")
    # fallback single "raw_" prefix if not in expected layout
    base = os.path.basename(object_name)
    return f"raw_{os.path.splitext(base)[0].lower()}"

def ingest_gcs_to_bq(event, context=None):
    """
    Cloud Functions (Gen2) background function.
    Triggered by Eventarc GCS finalize events.
    """
    # Eventarc delivers CloudEvent; handle both dict and cloudevents SDK types
    if hasattr(event, "data"):
        data = event.data
    else:
        data = event  # already a dict

    # GCS event payload
    bucket = data.get("bucket")
    name = data.get("name")

    # Filter: only process "raw/" prefix
    if not name or not name.startswith("raw/"):
        print(f"Skipping object outside 'raw/': {name}")
        return

    if not name.lower().endswith(".csv"):
        print(f"Skipping non-CSV: {name}")
        return

    uri = f"gs://{bucket}/{name}"
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{_table_name_from_path(name)}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        field_delimiter=",",
        quote_character='"',
        allow_quoted_newlines=True,
        encoding="UTF-8",
    )

    print(f"Loading {uri} -> {table_id}")
    load_job = bq.load_table_from_uri(uri, table_id, job_config=job_config)
    result = load_job.result()  # wait for job
    dest = bq.get_table(table_id)
    print(json.dumps({
        "table": table_id,
        "rows_loaded": result.output_rows,
        "total_rows": dest.num_rows
    }))
