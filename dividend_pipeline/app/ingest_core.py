import os
from pathlib import Path
import pyarrow.parquet as pq
from google.cloud import storage, bigquery

# Use the new normalization logic from normalize_dividends.py
from normalize_dividends import normalize_csv


# ---------- Local output ----------
def write_local_output(table, source_file: str):
    out_dir = Path("/data/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (Path(source_file).stem + ".parquet")
    pq.write_table(table, out_path)
    print(f"[LOCAL OUTPUT] Wrote {out_path}")


# ---------- BigQuery loader ----------
def load_to_bigquery(table, project: str, dataset: str = "finance", table_name: str = "etrade_dividends"):
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

    tmp_path = "/tmp/batch.parquet"
    pq.write_table(table, tmp_path)

    with open(tmp_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_cfg)
    job.result()

    print(f"[BIGQUERY] Loaded {table.num_rows} rows into {table_id}")


# ---------- Entrypoint ----------
def main():
    local_file = os.environ.get("LOCAL_FILE")
    if local_file:
        # Local mode: normalize + write to /data/out
        table = normalize_csv(local_file, source_file=local_file)
        write_local_output(table, local_file)
        return

    # Cloud mode: GCS download → normalize → optional upload/load
    bucket = os.environ["BUCKET"]
    object_name = os.environ["OBJECT"]
    project = os.environ.get("GCP_PROJECT")
    staging_bucket = os.environ.get("STAGING_BUCKET")

    storage_client = storage.Client()
    blob = storage_client.bucket(bucket).blob(object_name)

    local_path = f"/tmp/{Path(object_name).name}"
    blob.download_to_filename(local_path)
    print(f"[GCS] Downloaded gs://{bucket}/{object_name} -> {local_path}")

    table = normalize_csv(local_path, source_file=f"gs://{bucket}/{object_name}")

    if staging_bucket:
        pq_path = f"/tmp/{Path(object_name).stem}.parquet"
        pq.write_table(table, pq_path)
        dest = f"normalized/{Path(pq_path).name}"
        storage_client.bucket(staging_bucket).blob(dest).upload_from_filename(pq_path)
        print(f"[GCS] Uploaded normalized parquet to gs://{staging_bucket}/{dest}")

    if project:
        load_to_bigquery(table, project)
