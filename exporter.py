"""
exporter.py
===========
Exports the 82-column DataFrame to a CSV file named after the container
number.  Replicates the VBA duplicate-safe naming convention:

    <container_no>.csv          (first run)
    <container_no>_2.csv        (if above exists)
    <container_no>_3.csv        (and so on)

The CSV is written without pandas index and with latin-1 encoding to
match the original template file encoding.  The header row is always
included.

For the web/API use-case, the caller may pass output_dir=None to
receive the CSV content as a string instead of writing to disk.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_ENCODING = "latin-1"


class ExporterError(Exception):
    """Raised when the export cannot be completed."""


def _safe_filename(output_dir: Path, container_no: str) -> Path:
    base = output_dir / f"{container_no}.csv"
    if not base.exists():
        return base

    counter = 2
    while True:
        candidate = output_dir / f"{container_no}_{counter}.csv"
        if not candidate.exists():
            return candidate
        counter += 1


def _fix_artikelcode(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure Artikelcode column is EMPTY as required by Fiton.
    Does NOT modify original DataFrame structure.
    """
    if "Artikelcode" in df.columns:
        df = df.copy()
        df["Artikelcode"] = ""   # ✅ Force empty
    return df


def export_to_file(
    df: pd.DataFrame,
    container_no: str,
    output_dir: str | Path = "output",
) -> Path:
    if not container_no:
        raise ExporterError("Container number is empty – cannot determine output filename.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = _safe_filename(out_dir, container_no)

    try:
        # ✅ APPLY FIX HERE (ONLY CHANGE)
        df = _fix_artikelcode(df)

        df.to_csv(
            file_path,
            index=False,
            encoding=DEFAULT_ENCODING,
            lineterminator="\n",
        )
        logger.info("CSV exported → %s  (%d rows)", file_path, len(df))
        return file_path
    except Exception as exc:
        raise ExporterError(f"Failed to write CSV to '{file_path}': {exc}") from exc


def export_to_string(df: pd.DataFrame) -> str:
    buffer = io.StringIO()

    # ✅ APPLY FIX HERE ALSO
    df = _fix_artikelcode(df)

    df.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def export_to_bytes(df: pd.DataFrame, encoding: str = DEFAULT_ENCODING) -> bytes:
    buffer = io.StringIO()

    # ✅ APPLY FIX HERE ALSO
    df = _fix_artikelcode(df)

    df.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue().encode(encoding, errors="replace")
