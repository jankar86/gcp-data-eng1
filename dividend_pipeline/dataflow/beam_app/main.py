import argparse
row["pay_date"] = self._parse_date(row["pay_date"]) # required
if not row["pay_date"]:
    raise ValueError("pay_date required")
    except Exception:
    
    yield beam.pvalue.TaggedOutput("bad", {"row": row, "reason": "bad_pay_date"})
return


if row.get("ex_date"):
try:
row["ex_date"] = self._parse_date(row["ex_date"]) # nullable
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
parser.add_argument("--input", required=True) # gs://bucket/file.csv
parser.add_argument("--output_table", required=True) # project:dataset.table
parser.add_argument("--bad_rows_gcs", required=True) # gs://bucket/dir
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