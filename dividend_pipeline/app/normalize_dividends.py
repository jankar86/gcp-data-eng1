# normalize_dividends.py
import io, re, csv, json, chardet, pyarrow as pa, pyarrow.compute as pc, pyarrow.parquet as pq
import pandas as pd
from ruamel.yaml import YAML
from datetime import datetime
from schema_dividends import mk_row_hash

yaml = YAML(typ="safe")

def _auto_encoding(path):
    with open(path, "rb") as f:
        raw = f.read(4096)
    enc = chardet.detect(raw)["encoding"] or "utf-8"
    return enc

def _read_csv(path, cfg):
    enc = cfg.get("encoding", "auto")
    enc = _auto_encoding(path) if enc == "auto" else enc
    thousands = cfg.get("thousands", None)
    decimal = cfg.get("decimal", ".")
    # Robust CSV read (handles ragged rows)
    df = pd.read_csv(
        path,
        dtype=str,
        encoding=enc,
        on_bad_lines="skip",
        engine="python"
    ).fillna("")
    return df

def _to_decimal(s, negative_fmt):
    s = s.strip()
    if s == "": return None
    if negative_fmt == "paren" and s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    s = s.replace(",", "")
    try:
        return float(s)
    except:
        return None

def choose_profile(cfg, filename, header_row):
    for p in cfg["profiles"]:
        w = p.get("when", {})
        fn_ok = True
        if "filename_glob" in w:
            import fnmatch
            fn_ok = fnmatch.fnmatch(filename, w["filename_glob"])
        hdr_ok = True
        if "header_contains" in w:
            hdr_ok = all(h in header_row for h in w["header_contains"])
        if fn_ok and hdr_ok:
            return p
    return None

def normalize_csv(path, profile, source_file):
    reader = profile["reader"]
    mapping = profile["mapping"]
    negative_fmt = reader.get("negative_formats", ["minus"])
    if isinstance(negative_fmt, list): negative_fmt = negative_fmt[0]

    df = _read_csv(path, reader)
    if df.empty:
        return None, []

    header_row = list(df.columns)
    p = profile  # alias
    # Choose profile again with header check (safety)
    # (Optional—already done by caller)

    # Map columns
    out = pd.DataFrame()
    for raw_col, canon_col in mapping.get("columns", {}).items():
        if raw_col in df.columns:
            out[canon_col] = df[raw_col].astype(str).str.strip()
        else:
            out[canon_col] = ""

    # Constants
    for k, v in (mapping.get("constants") or {}).items():
        out[k] = v

    # Derived simple rules
    def contains(row, needle):
        # check across known textual columns
        return any(needle.lower() in str(row.get(c, "")).lower()
                   for c in df.columns)
    if "derived" in mapping:
        for k, expr in mapping["derived"].items():
            if expr.startswith("contains("):
                needle = expr.split(",",1)[1].strip(" )'\"")
                out[k] = df.apply(lambda r: contains(r, needle), axis=1)
            else:
                out[k] = ""

    # Coercions
    date_cols = ["ex_date","record_date","pay_date"]
    for c in date_cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.date

    # Numeric coercions with sign/locale handling
    for c in ["quantity","gross_amount","withholding_tax","fees","net_amount","drip_price"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda s: _to_decimal(str(s), negative_fmt))

    # Special rules: split E*TRADE tax/fee rows into amounts
    rules = mapping.get("rules", [])
    if rules:
        # Start with all zeros where missing
        for c in ["withholding_tax","fees"]:
            if c not in out.columns: out[c] = 0.0
        # Identify tax/fee rows by description and move Amount into correct bucket
        # If profile mapped "gross_amount", keep; else compute from net + components later
        desc_src = None
        for cand in ["Description","Activity","Memo","description","DESC"]:
            if cand in df.columns:
                desc_src = df[cand]; break
        if desc_src is not None and "gross_amount" in out.columns:
            mask_tax = desc_src.str.contains("Withholding", case=False, na=False)
            out.loc[mask_tax, "withholding_tax"] = out.loc[mask_tax, "gross_amount"].abs()
            out.loc[mask_tax, "gross_amount"] = 0.0

            mask_fee = desc_src.str.contains("ADR Fee|Fee", case=False, na=False)
            out.loc[mask_fee, "fees"] = out.loc[mask_fee, "gross_amount"].abs()
            out.loc[mask_fee, "gross_amount"] = 0.0

    # Compute net if missing
    if "net_amount" not in out.columns:
        for c in ["gross_amount","withholding_tax","fees"]:
            if c not in out.columns: out[c] = 0.0
        out["net_amount"] = (out["gross_amount"] or 0) - (out["withholding_tax"] or 0) - (out["fees"] or 0)

    # Ensure required fields present
    unmet = mapping.get("required", [])
    errs = []
    for r in unmet:
        if r not in out.columns:
            out[r] = None
    # Attach provenance
    out["source_file"] = source_file
    out["line_no"] = range(2, 2 + len(out))  # assuming header on line 1
    out["created_ts"] = pd.Timestamp.utcnow(tz=None)

    # row_hash
    out["row_hash"] = out.apply(lambda r: mk_row_hash(r.to_dict()), axis=1)

    # Minimal default columns
    def col(c): return out[c] if c in out.columns else None
    # Reorder to canonical + keep any extras as notes JSON
    known = set([
      "row_hash","account_id","broker","broker_account","symbol","cusip","isin","security_name",
      "event_type","ex_date","record_date","pay_date","quantity","gross_amount","withholding_tax",
      "fees","net_amount","currency","reinvested","drip_price","created_ts","source_file","line_no","notes"
    ])
    extras = out.drop(columns=[c for c in out.columns if c in known], errors="ignore")
    if not extras.empty:
        out["notes"] = extras.astype(str).to_dict(orient="records")
    else:
        out["notes"] = None

    # Return Arrow table for fast load
    table = pa.Table.from_pandas(out, preserve_index=False)
    return table, errs
