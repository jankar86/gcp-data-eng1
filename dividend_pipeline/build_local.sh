# Build
docker build -t div-ingest ./app/.

# Run interactively, mounting test-data into /data
docker run --rm -it \
  -v $PWD/app/test-data:/data \
  div-ingest \
  python main.py --bucket /data --object etrade-9153-8-22.csv --local
