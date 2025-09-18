# Build
docker build -t div-ingest ./app/.

# Run interactively, mounting test-data into /data
docker run --rm -it \
  -v $PWD/test-data:/data \
  div-ingest \
  python main.py --bucket /data --object fidelity_sample.csv --local
