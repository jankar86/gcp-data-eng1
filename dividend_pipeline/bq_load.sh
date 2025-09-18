bq load \
  --source_format=PARQUET \
  --project_id="data-eng-d-091625" \
  finance.etrade_dividends \
  ./app/test-data/out/etrade-9153-8-22.parquet
