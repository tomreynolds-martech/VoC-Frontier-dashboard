"""Data layer: load and normalise the CSV that ships inside the repo.

To update the dashboard, replace ``data/frontiers_responses.csv`` (keeping the
same column headers) and reload the app.
"""
from __future__ import annotations

import pandas as pd

from src import config


def _norm_key(s: str) -> str:
    """Collapse whitespace/newlines and lowercase, for tolerant header matching."""
    return " ".join(str(s).split()).lower()


def load_data(path: str | None = None) -> pd.DataFrame:
    """Read the repo CSV, rename headers to short field names, and coerce types."""
    df = pd.read_csv(path or config.DATA_CSV)

    lookup = {_norm_key(raw): short for raw, short in config.COLUMN_MAP.items()}
    rename = {col: lookup[_norm_key(col)] for col in df.columns
              if _norm_key(col) in lookup}
    df = df.rename(columns=rename)

    # Keep known fields that are present, in a stable order.
    known = [c for c in config.COLUMN_MAP.values() if c in df.columns]
    df = df[known].copy()

    # Types
    if "response_date" in df:
        df["response_date"] = pd.to_datetime(df["response_date"], errors="coerce")
    for fld in config.SCORE_FIELDS:
        if fld in df:
            df[fld] = pd.to_numeric(df[fld], errors="coerce")
    for fld in config.TEXT_FIELDS:
        if fld in df:
            df[fld] = df[fld].astype("string")

    df = df.reset_index(drop=True)
    df.insert(0, "record_id", range(1, len(df) + 1))
    return df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Render a (possibly filtered) DataFrame back to CSV with original headers."""
    inverse = {v: k for k, v in config.COLUMN_MAP.items()}
    out = df.drop(columns=[c for c in ["record_id"] if c in df.columns]).copy()
    out = out.rename(columns={c: inverse.get(c, c) for c in out.columns})
    return out.to_csv(index=False).encode("utf-8")
