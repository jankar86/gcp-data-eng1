# Build
docker build -t div-ingest ./app/.

# Run interactively, mounting test-data into /data
docker run --rm -it \
  -v $PWD/app/test-data:/data \
  div-ingest \
  python main.py --bucket /data --object etrade-9153-7-3-24_6-5-25.csv --local
