FROM python:3.9-slim

WORKDIR /app

# Install pyarrow only (pandas optional if you want row preview)
RUN pip install --no-cache-dir pyarrow pandas

COPY inspect_parquet.py .

ENTRYPOINT ["python", "inspect_parquet.py"]
