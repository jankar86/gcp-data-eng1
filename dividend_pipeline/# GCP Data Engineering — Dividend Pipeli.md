# GCP Data Engineering — Dividend Pipeline (Starter Kit)

A minimal-but-real cloud-native pipeline to ingest dividend CSVs from GCS → validate/transform with Dataflow (Apache Beam) → load into BigQuery, with orchestration trigger via Cloud Functions (2nd gen) on GCS finalize events. Terraform provisions infra; Docker+Flex Template packages the Beam job.

---

## 1) Architecture (MVP)

```
[Local/CI Upload]
       |
       v
+----------------+             GCS Object Finalize            +-----------------------+
|  GCS bucket    | --Event-->  Pub/Sub (via Notification) --> | Cloud Function (Gen2) | --launch--> Dataflow Flex Template
|  gs://dividends-raw-<proj>   topic: gcs.dividends.raw       |  launcher             |
+----------------+                                              +-----------------------+
                                                                               |
                                                                               v
                                                                  +---------------------+
                                                                  |  Dataflow (Beam)    |
                                                                  |  - Read CSV         |
                                                                  |  - Validate/Parse   |
                                                                  |  - Map to schema    |
                                                                  |  - Write to BQ      |
                                                                  |  - Bad rows -> GCS  |
                                                                  +---------------------+
                                                                               |
                                                                               v
                                                                  +---------------------+
                                                                  | BigQuery dataset    |
                                                                  |   dividends.fact    |
                                                                  +---------------------+
```

**Buckets**: `dividends-raw-<proj>`, `dividends-dlq-<proj>`, `dataflow-staging-<proj>`, `dataflow-temp-<proj>`
**Pub/Sub**: `gcs.dividends.raw` (events from raw bucket)
**BQ**: dataset `dividends`, table `fact_dividends`
**Runtimes**: Dataflow Flex Template (Beam Python 3.11), Cloud Functions Gen2 (Python 3.11)

---

## 2) Repo Layout

```
dividend-pipeline/
├─ terraform/
│  ├─ main.tf
│  ├─ variables.tf
│  ├─ outputs.tf
│  └─ versions.tf
├─ dataflow/
│  ├─ beam_app/
│  │  ├─ main.py
│  │  ├─ schema.py
│  │  └─ requirements.txt
│  ├─ Dockerfile
│  └─ flex_template_spec.json
├─ function_launcher/
│  ├─ main.py
│  ├─ requirements.txt
│  └─ README.md
├─ samples/
│  └─ sample_dividends.csv
└─ Makefile
```

---

## 3) Terraform (core resources)

> **Note:** Replace `project_id`, `region`, and naming as you like. This is a single-project setup. Service Accounts are minimal for MVP.

### `versions.tf`

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.39.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

### `variables.tf`

```hcl
variable "project_id" { type = string }
variable "region"     { type = string  default = "us-central1" }

variable "raw_bucket"     { type = string default = null }
variable "dlq_bucket"     { type = string default = null }
variable "staging_bucket" { type = string default = null }
variable "temp_bucket"    { type = string default = null }

locals {
  raw_bucket     = coalesce(var.raw_bucket,     "dividends-raw-${var.project_id}")
  dlq_bucket     = coalesce(var.dlq_bucket,     "dividends-dlq-${var.project_id}")
  staging_bucket = coalesce(var.staging_bucket, "dataflow-staging-${var.project_id}")
  temp_bucket    = coalesce(var.temp_bucket,    "dataflow-temp-${var.project_id}")
}
```

### `main.tf`

```hcl
# Enable required services
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "dataflow.googleapis.com",
    "eventarc.googleapis.com",
    "run.googleapis.com",
    "cloudfunctions.googleapis.com"
  ])
  service = each.key
}

# Buckets
resource "google_storage_bucket" "raw" {
  name                        = local.raw_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket" "dlq" {
  name                        = local.dlq_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket" "staging" {
  name                        = local.staging_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket" "temp" {
  name                        = local.temp_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# Pub/Sub notification from GCS (object finalize)
resource "google_pubsub_topic" "gcs_raw" {
  name = "gcs.dividends.raw"
}

resource "google_storage_notification" "raw_finalize" {
  bucket         = google_storage_bucket.raw.name
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.gcs_raw.id
  event_types    = ["OBJECT_FINALIZE"]
}

# BigQuery dataset + table
resource "google_bigquery_dataset" "dividends" {
  dataset_id                 = "dividends"
  location                   = "US"
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "fact_dividends" {
  dataset_id = google_bigquery_dataset.dividends.dataset_id
  table_id   = "fact_dividends"
  deletion_protection = false
  schema = jsonencode([
    {"name":"source_filename","type":"STRING","mode":"REQUIRED"},
    {"name":"load_ts","type":"TIMESTAMP","mode":"REQUIRED"},
    {"name":"account_id","type":"STRING","mode":"REQUIRED"},
    {"name":"ticker","type":"STRING","mode":"REQUIRED"},
    {"name":"ex_date","type":"DATE","mode":"NULLABLE"},
    {"name":"pay_date","type":"DATE","mode":"REQUIRED"},
    {"name":"amount","type":"NUMERIC","mode":"REQUIRED"},
    {"name":"currency","type":"STRING","mode":"NULLABLE"},
    {"name":"shares","type":"NUMERIC","mode":"NULLABLE"},
    {"name":"broker","type":"STRING","mode":"NULLABLE"},
    {"name":"notes","type":"STRING","mode":"NULLABLE"}
  ])
}

# Service Accounts
resource "google_service_account" "dataflow_sa" {
  account_id   = "dataflow-worker-sa"
  display_name = "Dataflow Worker SA"
}

resource "google_service_account" "function_sa" {
  account_id   = "dividends-launcher-sa"
  display_name = "CFn2 Launcher SA"
}

# IAM for SA
resource "google_project_iam_member" "dataflow_roles" {
  for_each = toset([
    "roles/dataflow.worker",
    "roles/dataflow.developer",
    "roles/storage.objectAdmin",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser"
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "function_roles" {
  for_each = toset([
    "roles/dataflow.developer",
    "roles/storage.objectViewer",
    "roles/pubsub.subscriber",
    "roles/run.invoker",
    "roles/iam.serviceAccountUser"
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Cloud Function (Gen2) to launch Dataflow Flex Template
resource "google_cloudfunctions2_function" "launcher" {
  name        = "dividends-flex-launcher"
  location    = var.region
  description = "Launch Dataflow Flex on GCS finalize"

  build_config {
    runtime     = "python311"
    entry_point = "entrypoint"
    source {
      storage_source {
        bucket = google_storage_bucket.staging.name
        object = "function_launcher_src.zip"
      }
    }
  }

  service_config {
    max_instance_count = 3
    available_memory   = "512M"
    timeout_seconds    = 540
    service_account_email = google_service_account.function_sa.email
    environment_variables = {
      FLEX_TEMPLATE_GCS_PATH = "gs://${google_storage_bucket.staging.name}/flex_templates/dividends_spec.json"
      DATAFLOW_TEMP_LOCATION = "gs://${google_storage_bucket.temp.name}/temp"
      DATAFLOW_STAGING_LOCATION = "gs://${google_storage_bucket.staging.name}/staging"
      DATAFLOW_REGION = var.region
      BQ_DATASET = google_bigquery_dataset.dividends.dataset_id
      BQ_TABLE   = google_bigquery_table.fact_dividends.table_id
      DLQ_BUCKET = google_storage_bucket.dlq.name
      WORKER_SA  = google_service_account.dataflow_sa.email
      PROJECT_ID = var.project_id
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.gcs_raw.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}
```

### `outputs.tf`

```hcl
output "raw_bucket" { value = google_storage_bucket.raw.name }
output "dlq_bucket" { value = google_storage_bucket.dlq.name }
output "staging_bucket" { value = google_storage_bucket.staging.name }
output "temp_bucket" { value = google_storage_bucket.temp.name }
output "pubsub_topic" { value = google_pubsub_topic.gcs_raw.name }
output "function_name" { value = google_cloudfunctions2_function.launcher.name }
output "bq_table" { value = "${google_bigquery_dataset.dividends.dataset_id}.${google_bigquery_table.fact_dividends.table_id}" }
```

---

## 4) Cloud Function (launcher) — `function_launcher/main.py`

```python
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
```

### `function_launcher/requirements.txt`

```
google-api-python-client==2.135.0
```

> Package to staging bucket as `function_launcher_src.zip` (see Makefile below).

---

## 5) Dataflow (Beam) — Flex Template

### `dataflow/beam_app/requirements.txt`

```
apache-beam[gcp]==2.57.0
python-dateutil
```

### `dataflow/beam_app/schema.py`

```python
from typing import Dict

BQ_SCHEMA = {
    "fields": [
        {"name": "source_filename", "type": "STRING", "mode": "REQUIRED"},
        {"name": "load_ts", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "ticker", "type": "STRING", "mode": "REQUIRED"},
        {"name": "ex_date", "type": "DATE", "mode": "NULLABLE"},
        {"name": "pay_date", "type": "DATE", "mode": "REQUIRED"},
        {"name": "amount", "type": "NUMERIC", "mode": "REQUIRED"},
        {"name": "currency", "type": "STRING", "mode": "NULLABLE"},
        {"name": "shares", "type": "NUMERIC", "mode": "NULLABLE"},
        {"name": "broker", "type": "STRING", "mode": "NULLABLE"},
        {"name": "notes", "type": "STRING", "mode": "NULLABLE"}
    ]
}
```

### `dataflow/beam_app/main.py`

```python
import argparse
import csv
import io
import os
from datetime import datetime
from typing import Dict, Iterable, Tuple

import apache_beam as beam
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.options.pipeline_options import PipelineOptions
from dateutil.parser import parse as parse_dt

from schema import BQ_SCHEMA

REQUIRED_COLUMNS = [
    "account_id", "ticker", "pay_date", "amount"
]

class ParseCSV(beam.DoFn):
    def process(self, element: Tuple[str, bytes]) -> Iterable[Dict]:
        filename, content = element
        text = content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield {
                "source_filename": filename,
                "load_ts": datetime.utcnow().isoformat(),
                "account_id": (row.get("account_id") or "").strip(),
                "ticker": (row.get("ticker") or "").strip(),
                "ex_date": (row.get("ex_date") or "").strip() or None,
                "pay_date": (row.get("pay_date") or "").strip(),
                "amount": (row.get("amount") or "").strip(),
                "currency": (row.get("currency") or "USD").strip() or None,
                "shares": (row.get("shares") or "").strip() or None,
                "broker": (row.get("broker") or "").strip() or None,
                "notes": (row.get("notes") or "").strip() or None,
            }

class ValidateTransform(beam.DoFn):
    def __init__(self, bad_rows_dir: str):
        self.bad_rows_dir = bad_rows_dir.rstrip("/")

    def _is_missing(self, r: Dict) -> bool:
        return any(not r.get(c) for c in REQUIRED_COLUMNS)

    def _parse_date(self, s: str):
        if not s:
            return None
        return parse_dt(s).date().isoformat()

    def process(self, row: Dict) -> Iterable[Dict]:
        # Required fields present
        if self._is_missing(row):
            yield beam.pvalue.TaggedOutput("bad", {"row": row, "reason": "missing_required"})
            return
        # Normalize types
        try:
            row["amount"] = str(round(float(row["amount"]), 6))
        except Exception:
            yield beam.pvalue.TaggedOutput("bad", {"row": row, "reason": "bad_amount"})
            return

        try:
            row["pay_date"] = self._parse_date(row["pay_date"])  # required
            if not row["pay_date"]:
                raise ValueError("pay_date required")
        except Exception:
            yield beam.pvalue.TaggedOutput("bad", {"row": row, "reason": "bad_pay_date"})
            return

        if row.get("ex_date"):
            try:
                row["ex_date"] = self._parse_date(row["ex_date"])  # nullable
            except Exception:
                row["ex_date"] = None

        if row.get("shares"):
            try:
                row["shares"] = str(round(float(row["shares"]), 6))
            except Exception:
                row["shares"] = None

        yield row

class GCSBadRowSink(beam.DoFn):
    def __init__(self, bad_rows_dir: str):
        self.bad_rows_dir = bad_rows_dir.rstrip("/")

    def process(self, element: Dict):
        from apache_beam.io.gcp.gcsio import GcsIO
        gcs = GcsIO()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        path = f"{self.bad_rows_dir}/badrow-{ts}.json"
        import json
        gcs.open(path, "w").write((json.dumps(element) + "\n").encode("utf-8"))
        yield beam.pvalue.TaggedOutput("written", path)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)  # gs://bucket/file.csv
    parser.add_argument("--output_table", required=True)  # project:dataset.table
    parser.add_argument("--bad_rows_gcs", required=True)  # gs://bucket/dir
    parser.add_argument("--temp_location", required=False)
    parser.add_argument("--staging_location", required=False)

    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args, save_main_session=True, streaming=False)

    with beam.Pipeline(options=options) as p:
        file_pc = (
            p
            | "ReadFile" >> beam.io.ReadFromText(known_args.input, strip_trailing_newlines=False)
        )
        # Beam ReadFromText returns lines; instead load binary content via FileSystems
        from apache_beam.io.filesystems import FileSystems
        file_metadata = FileSystems.match([known_args.input])[0].metadata_list[0]
        content = FileSystems.open(file_metadata.path).read()

        rows = (
            p
            | "CreateSingle" >> beam.Create([(os.path.basename(file_metadata.path), content)])
            | "ParseCSV" >> beam.ParDo(ParseCSV())
        )

        good = rows | "Validate" >> beam.ParDo(ValidateTransform(known_args.bad_rows_gcs)).with_outputs("bad", main="good")

        bad = good.bad | "WriteBadRows" >> beam.ParDo(GCSBadRowSink(known_args.bad_rows_gcs))

        (
            good.good
            | "WriteBQ" >> WriteToBigQuery(
                known_args.output_table,
                schema=BQ_SCHEMA,
                write_disposition=WriteToBigQuery.WriteDisposition.WRITE_APPEND,
                create_disposition=WriteToBigQuery.CreateDisposition.CREATE_NEVER,
            )
        )

if __name__ == "__main__":
    run()
```

### `dataflow/Dockerfile`

```dockerfile
FROM apache/beam_python3.11_sdk:2.57.0

WORKDIR /opt/app
COPY beam_app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY beam_app/ ./
ENTRYPOINT ["python", "-m", "main"]
```

### `dataflow/flex_template_spec.json`

```json
{
  "image": "gcr.io/PROJECT_ID/dividends-beam:latest",
  "metadata": {
    "name": "Dividends CSV → BigQuery",
    "parameters": [
      {"name": "input", "label": "GCS CSV path", "helpText": "gs://bucket/file.csv", "paramType": "TEXT", "isOptional": false},
      {"name": "output_table", "label": "BQ table", "helpText": "project:dataset.table", "paramType": "TEXT", "isOptional": false},
      {"name": "bad_rows_gcs", "label": "Bad rows dir", "helpText": "gs://bucket/dir", "paramType": "TEXT", "isOptional": false},
      {"name": "temp_location", "label": "Temp location", "paramType": "TEXT", "isOptional": true},
      {"name": "staging_location", "label": "Staging location", "paramType": "TEXT", "isOptional": true}
    ]
  }
}
```

> Replace `PROJECT_ID` during build (Makefile handles this) and upload the spec to `gs://dataflow-staging-<proj>/flex_templates/dividends_spec.json`.

---

## 6) Makefile (helper targets)

```makefile
PROJECT_ID ?= your-project-id
REGION ?= us-central1
STAGING_BUCKET ?= dataflow-staging-$(PROJECT_ID)
TEMPLATE_SPEC ?= gs://$(STAGING_BUCKET)/flex_templates/dividends_spec.json
IMAGE ?= gcr.io/$(PROJECT_ID)/dividends-beam:latest

.PHONY: build-pipeline push-pipeline publish-template pack-function tf-init tf-plan tf-apply upload-sample

build-pipeline:
	cd dataflow && docker build -t $(IMAGE) .

push-pipeline:
	docker push $(IMAGE)

publish-template:
	gsutil cp dataflow/flex_template_spec.json /tmp/flex_spec.json
	python3 - << 'EOF'
import json, os
p = "/tmp/flex_spec.json"
with open(p) as f: spec = json.load(f)
spec["image"] = os.environ.get("IMAGE")
open(p, "w").write(json.dumps(spec))
EOF
	gsutil cp /tmp/flex_spec.json $(TEMPLATE_SPEC)

pack-function:
	cd function_launcher && zip -r /tmp/function_launcher_src.zip .
	gsutil cp /tmp/function_launcher_src.zip gs://$(STAGING_BUCKET)/function_launcher_src.zip

tf-init:
	cd terraform && terraform init

tf-plan:
	cd terraform && terraform plan

tf-apply:
	cd terraform && terraform apply -auto-approve

upload-sample:
	gsutil cp samples/sample_dividends.csv gs://dividends-raw-$(PROJECT_ID)/
```

---

## 6.1) Terraform tfvars setup (safe-by-default)

Create a private `terraform.tfvars` (auto-loaded by Terraform) and keep it **out of source control**.

\`\`

```gitignore
# Local state & caches
.terraform/
.terraform.lock.hcl

# Private variables (do not commit)
terraform.tfvars
*.auto.tfvars
env/*.tfvars
```

\`\` (commit this example, not your real values)

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"

# Optional: override bucket names; null means use defaults from locals
raw_bucket     = null
dlq_bucket     = null
staging_bucket = null
temp_bucket    = null
```

Now create your private file:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your real values
```

Because the file name is `terraform.tfvars`, Terraform **automatically loads** it. No need to pass `-var-file` each time.

**Apply using the Makefile** (now relies on tfvars):

```bash
make tf-init
make tf-plan
make tf-apply
```

> If you prefer environment-specific files, you can use `dev.auto.tfvars`, `prod.auto.tfvars` etc. Files with the suffix `.auto.tfvars` are also auto-loaded. For multiple environments, keep them in `terraform/env/` and only keep **one** `.auto.tfvars` present at a time, or specify with `-var-file=env/dev.tfvars` explicitly.

---

## 7) Sample CSV — `samples/sample_dividends.csv` — `samples/sample_dividends.csv`

```csv
account_id,ticker,ex_date,pay_date,amount,currency,shares,broker,notes
F12345,TROW,2024-03-14,2024-03-28,12.50,USD,10,Fidelity,Quarterly dividend
F12345,OHI,2024-05-15,2024-05-30,7.80,USD,20,Fidelity,
E99999,SCHD,2024-06-20,2024-06-24,15.10,USD,5,E*TRADE,ETF payout
```

---

## 8) End-to-End Bring-up Steps

1. **Auth & Project**: `gcloud config set project <PROJECT_ID>` and ensure you have Owner or sufficient roles.
2. **Terraform**: `make tf-init tf-apply PROJECT_ID=<proj> REGION=us-central1`
3. **Build & Push Beam Image**: `make build-pipeline push-pipeline PROJECT_ID=<proj>` (ensure `gcloud auth configure-docker`)
4. **Publish Flex Template**: `make publish-template PROJECT_ID=<proj>`
5. **Package Function**: `make pack-function PROJECT_ID=<proj>`
6. **Test**: `make upload-sample PROJECT_ID=<proj>` → This uploads `sample_dividends.csv` to raw bucket, triggers CF → launches Dataflow → writes to BQ.
7. **Verify**: In BigQuery: `SELECT * FROM \   \   \   `.dividends.fact\_dividends` ORDER BY load_ts DESC LIMIT 100;`

---

## 9) IAM/Perm Notes (least-privilege later)

* **Dataflow SA**: `roles/dataflow.worker`, `roles/storage.objectAdmin`, `roles/bigquery.dataEditor`, `roles/bigquery.jobUser`.
* **Function SA**: `roles/dataflow.developer`, `roles/pubsub.subscriber`, `roles/storage.objectViewer`, `roles/run.invoker`, `roles/iam.serviceAccountUser`.
* Consider scoping Storage perms to specific buckets.

---

## 10) Extensions (nice-to-have)

* **Schema registry**: versioned JSON schema in repo; validate headers/column drift.
* **DLQ**: write bad rows to BigQuery table `dividends.bad_rows` in addition to GCS.
* **Composer/Airflow**: orchestrate batch backfills (list GCS and launch jobs per file).
* **Data Catalog**: tag dataset/table with owners, PII flags.
* **CI/CD**: Cloud Build or GitHub Actions to build/push image and apply Terraform.
* **Partitioning**: Partition table by `pay_date` and cluster by `ticker`.

---

## 11) Partitioned Table Variant (optional)

```hcl
resource "google_bigquery_table" "fact_dividends" {
  dataset_id = google_bigquery_dataset.dividends.dataset_id
  table_id   = "fact_dividends"
  time_partitioning {
    type  = "DAY"
    field = "pay_date"
  }
  clustering = ["ticker"]
  schema = jsonencode(/* same as above */)
}
```

---

## 12) Troubleshooting

* Cloud Function logs show `Skipping non-CSV`: ensure file extension is `.csv`.
* Dataflow job failing on schema: confirm BQ table created and `CREATE_NEVER` is intended; set to `CREATE_IF_NEEDED` during first run.
* Permission denied on buckets: verify SA roles and bucket-level IAM for UBLE.
* CSV header mismatch: ensure columns include at least `account_id,ticker,pay_date,amount`.

---

**You can now paste this starter kit into a new repo and run the Makefile targets in order.**
