import sys
import pyarrow.parquet as pq

if len(sys.argv) < 2:
    print("Usage: python inspect_parquet.py <file.parquet>")
    sys.exit(1)

path = sys.argv[1]
pf = pq.ParquetFile(path)

print("\n=== Parquet Schema (raw) ===")
print(pf.schema)

print("\n=== Arrow Schema ===")
arrow_schema = pf.schema_arrow
print(arrow_schema)

print("\n=== TransactionDate field type (Arrow) ===")
try:
    field = arrow_schema.field("TransactionDate")
    print("TransactionDate:", field.type)
except KeyError:
    print("TransactionDate not found in schema!")

print("\n=== First 5 rows ===")
print(pf.read_row_group(0).to_pandas().head())
