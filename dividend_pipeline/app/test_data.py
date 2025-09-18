import pandas as pd
df = pd.read_parquet("test-data/out/etrade-9153-8-22.parquet")
print(df.dtypes)
print(df.head())
