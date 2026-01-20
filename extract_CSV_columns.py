from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import pandas as pd


def extract_csv_columns(
    csv_path: Union[str, Path],
    *,
    encoding: Optional[str] = None,
    separator: Optional[str] = None,
) -> List[str]:
    """
    Return column names from a CSV file.

    - Uses a lightweight read (nrows=0), so it doesn't load full data.
    - If separator is not provided, pandas will try to infer it.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    read_kwargs = {}
    if encoding is not None:
        read_kwargs["encoding"] = encoding

    if separator is None:
        # infer delimiter (works well for comma/semicolon/tab)
        df = pd.read_csv(path, nrows=0, sep=None, engine="python", **read_kwargs)
    else:
        df = pd.read_csv(path, nrows=0, sep=separator, **read_kwargs)

    return [str(c) for c in df.columns.tolist()]


def extract_csv_columns_from_many(
    csv_paths: Sequence[Union[str, Path]],
    *,
    encoding: Optional[str] = None,
    separator: Optional[str] = None,
) -> List[str]:
    """Return a de-duplicated list of columns across multiple CSV files (preserves order)."""
    seen = set()
    out: List[str] = []
    for p in csv_paths:
        cols = extract_csv_columns(p, encoding=encoding, separator=separator)
        for c in cols:
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out


def build_facts_from_csv_and_events(
    csv_path: Union[str, Path],
    events: List[Dict[str, Any]],
    *,
    domain_context: str = "Drone flight test",
    encoding: Optional[str] = None,
    separator: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a facts dict suitable for LLM prompting.

    - `stats` includes min/max for every numeric column found in the CSV.
    - `events_detected` is the output of `detect_events(...)`.

    Notes:
    - This function does not call `detect_events` itself; you pass `events` in.
    - Non-numeric columns are skipped.
    """

    cols = extract_csv_columns(csv_path, encoding=encoding, separator=separator)

    # Load only needed columns; this is still simple and robust for a POC.
    df = pd.read_csv(csv_path, sep=separator, encoding=encoding) if separator else pd.read_csv(csv_path, sep=None, engine="python", encoding=encoding)

    stats: Dict[str, float] = {}
    for c in cols:
        if c not in df.columns:
            continue
        s = df[c]
        if not pd.api.types.is_numeric_dtype(s):
            continue
        s2 = pd.to_numeric(s, errors="coerce")
        if s2.notna().any():
            stats[f"{c}_min"] = float(s2.min())
            stats[f"{c}_max"] = float(s2.max())

    return {
        "stats": stats,
        "events_detected": events,
        "domain_context": domain_context,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Print CSV column names.")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--encoding", default=None, help="Optional encoding (e.g., utf-8, cp1255)")
    parser.add_argument("--sep", default=None, help="Optional separator (e.g., ',', ';', '\\t')")
    args = parser.parse_args()

    cols = extract_csv_columns(args.csv, encoding=args.encoding, separator=args.sep)
    print("Columns:")
    for c in cols:
        print(f"- {c}")


if __name__ == "__main__":
    main()