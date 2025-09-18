import os
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage, bigquery


def normalize_csv(path: str):
    """
    Very simple normalizer:
    - Reads CSV into pandas
    - Returns as Arrow table
    You’ll expand this with your broker-specific mappings.
    """
    df = pd.read_csv(path, dtype=str).fillna("")
    print(f"[NORMALIZE] Loaded {len(df)} rows from {path}")
    return pa.Table.from_pandas(df, preserve_index=False)


def write_local_output(table: pa.Table, source_file: str):
    """Write normalized Parquet locally (for testing)."""
    out_dir = Path("/data/out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / (Path(source_file).stem + ".parquet")
    pq.write_table(table, out_path)
    print(f"[LOCAL OUTPUT] Wrote {out_path}")


def load_to_bigquery(table: pa.Table, project: str, dataset: str = "finance", table_name: str = "dividends_fact"):
    """Append Parquet to BigQuery table."""
    client = bigquery.Client(project=project)
    table_id = f"{project}.{dataset}.{table_name}"
    job_cfg = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition="WRITE_APPEND",
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
        ],
    )
    # Write temp Parquet
    tmp_path = "/tmp/batch.parquet"
    pq.write_table(table, tmp_path)
    with open(tmp_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_cfg)
    job.result()
    print(f"[BIGQUERY] Loaded {table.num_rows} rows into {table_id}")


def main():
    # Local mode
    local_file = os.environ.get("LOCAL_FILE")
    if local_file:
        table = normalize_csv(local_file)
        write_local_output(table, local_file)
        return

    # Cloud mode
    bucket = os.environ["BUCKET"]
    object_name = os.environ["OBJECT"]
    project = os.environ.get("GCP_PROJECT")

    storage_client = storage.Client()
    blob = storage_client.bucket(bucket).blob(object_name)

    # Download to temp
    local_path = f"/tmp/{Path(object_name).name}"
    blob.download_to_filename(local_path)
    print(f"[GCS] Downloaded gs://{bucket}/{object_name} -> {local_path}")

    table = normalize_csv(local_path)

    # Write normalized parquet to staging bucket (optional)
    staging_bucket = os.environ.get("STAGING_BUCKET")
    if staging_bucket:
        pq_path = f"/tmp/{Path(object_name).stem}.parquet"
        pq.write_table(table, pq_path)
        dest = f"normalized/{Path(pq_path).name}"
        storage_client.bucket(staging_bucket).blob(dest).upload_from_filename(pq_path)
        print(f"[GCS] Uploaded normalized parquet to gs://{staging_bucket}/{dest}")

    # Load to BigQuery
    if project:
        load_to_bigquery(table, project)
