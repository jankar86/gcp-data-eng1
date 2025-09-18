import argparse
import base64
import json
import os
from flask import Flask, request

import ingest_core  # your normalization + BQ load logic

app = Flask(__name__)

def run_pipeline(bucket: str, object_name: str, local: bool = False):
    """
    Run the ingest pipeline.
    If local=True, treat bucket as a local folder and object_name as a file path.
    Otherwise, treat bucket/object as GCS.
    """
    if local:
        # Provide file path via env so ingest_core can branch
        os.environ["LOCAL_FILE"] = os.path.join(bucket, object_name)
        print(f"[LOCAL INGEST] Processing {os.environ['LOCAL_FILE']}")
    else:
        os.environ["BUCKET"] = bucket
        os.environ["OBJECT"] = object_name
        print(f"[CLOUD INGEST] Processing gs://{bucket}/{object_name}")

    ingest_core.main()

@app.route("/", methods=["POST"])
def handle_eventarc():
    envelope = request.get_json()
    if not envelope or "message" not in envelope:
        return "Bad Request", 400

    payload = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
    event = json.loads(payload)
    bucket = event.get("bucket")
    name   = event.get("name")

    run_pipeline(bucket, name, local=False)
    return "OK", 200

def cli():
    parser = argparse.ArgumentParser(description="Run dividend ingest locally")
    parser.add_argument("--bucket", required=True, help="Local folder path or GCS bucket")
    parser.add_argument("--object", required=True, help="Local file name or GCS object path")
    parser.add_argument("--local", action="store_true", help="Use local mode instead of GCS")
    args = parser.parse_args()

    run_pipeline(args.bucket, args.object, local=args.local)

if __name__ == "__main__":
    if os.environ.get("PORT"):  # Cloud Run mode
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
    else:  # CLI mode
        cli()
