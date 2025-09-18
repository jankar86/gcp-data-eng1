# Dockerfile
FROM python:3.11-slim

# Install system deps (for CSVs/Excel etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 libmagic1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy in your source code
COPY . .

# Non-root for security
RUN useradd -m worker
USER worker

EXPOSE 8080

# Default to running HTTP entrypoint for Cloud Run
CMD ["python", "main.py"]
