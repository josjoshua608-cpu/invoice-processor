"""
main.py
=======
Orchestrator for the invoice processing pipeline.

Usage (CLI):
    python main.py --input path/to/invoice.xlsx
    python main.py --input path/to/invoice.xlsx --output ./output
    python main.py --input path/to/invoice.xlsx --bl EGLV143656438208 --ucr NE34554B-FBA15LCL0MXQ

The process_invoice() function is also importable for web/API use:

    from main import process_invoice
    file_path = export_to_file(...)
    csv_bytes  = export_to_bytes(...)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from file_loader      import load_workbook_safe, detect_sheets
from header_extractor import extract_headers
from column_detector  import detect_header_row_and_hs_col, detect_data_columns
from aggregator       import aggregate
from packing_matcher  import build_package_totals
from csv_mapper       import build_dataframe
from exporter         import export_to_file, export_to_bytes

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core pipeline function (importable for web / API)
# ---------------------------------------------------------------------------
def process_invoice(
    file_path: str | Path,
    output_dir: str | Path = "output",
    bill_of_lading: str = "",
    ucr: str = "",
) -> dict:
    """
    Full invoice processing pipeline.

    Args:
        file_path:      Path to the source Excel (.xlsx) file.
        output_dir:     Directory for CSV output.
        bill_of_lading: Transport document reference (col 38 in CSV).
                        If empty, left blank.
        ucr:            UCR / zending reference (col 48 in CSV).
                        If empty, left blank.

    Returns:
        dict with keys:
            "output_path"   – Path object of the written CSV (str-able)
            "container_no"  – Detected container number
            "invoice_no"    – Detected invoice number
            "row_count"     – Number of data rows in output
            "df"            – The 82-column DataFrame (for API streaming)
    """
    logger.info("=== Invoice Processing Start ===")
    logger.info("Input file: %s", file_path)

    # ------------------------------------------------------------------
    # 1. Load workbook
    # ------------------------------------------------------------------
    wb = load_workbook_safe(file_path)

    # ------------------------------------------------------------------
    # 2. Detect sheets
    # ------------------------------------------------------------------
    invoice_ws, packing_ws = detect_sheets(wb)

    # ------------------------------------------------------------------
    # 3. Extract header-level metadata
    # ------------------------------------------------------------------
    invoice_no, container_no, currency, country = extract_headers(invoice_ws)
    logger.info(
        "Headers → invoice_no=%r  container_no=%r  currency=%r  country=%r",
        invoice_no, container_no, currency, country,
    )

    # ------------------------------------------------------------------
    # 4. Detect header row + column positions
    # ------------------------------------------------------------------
    header_row, col_hs_detected = detect_header_row_and_hs_col(invoice_ws)
    cols = detect_data_columns(invoice_ws, header_row)
    # col_hs from detect_header_row_and_hs_col is already stored in cols["hs"]
    # but we set it explicitly in case detect_data_columns missed it
    if cols["hs"] == 0:
        cols["hs"] = col_hs_detected

    logger.info("Header row: %d  |  columns: %s", header_row, cols)

    # ------------------------------------------------------------------
    # 5. Aggregate HS codes
    # ------------------------------------------------------------------
    aggregated = aggregate(
        ws         = invoice_ws,
        header_row = header_row,
        col_hs     = cols["hs"],
        col_desc   = cols["desc"],
        col_qty    = cols["qty"],
        col_val    = cols["val"],
        col_net    = cols["net"],
        col_gross  = cols["gross"],
    )

    if not aggregated:
        logger.error("No aggregatable rows found – check HS Code column detection.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 6. Match packing list → package totals
    # ------------------------------------------------------------------
    pkg_totals = build_package_totals(packing_ws, aggregated)

    # ------------------------------------------------------------------
    # 7. Build 82-column DataFrame
    # ------------------------------------------------------------------
    df = build_dataframe(
        aggregated     = aggregated,
        pkg_totals     = pkg_totals,
        invoice_no     = invoice_no,
        container_no   = container_no,
        currency       = currency,
        country        = country,
        bill_of_lading = bill_of_lading,
        ucr            = ucr,
    )

    # ------------------------------------------------------------------
    # 8. Export CSV
    # ------------------------------------------------------------------
    out_path = export_to_file(df, container_no, output_dir)
    logger.info("=== Processing Complete ===")
    logger.info("Output: %s", out_path)

    wb.close()

    return {
        "output_path": out_path,
        "container_no": container_no,
        "invoice_no": invoice_no,
        "row_count": len(df),
        "df": df,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convert an invoice Excel file to the 82-column customs CSV format."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the source Excel (.xlsx) invoice file.",
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Directory for the output CSV (default: ./output).",
    )
    parser.add_argument(
        "--bl",
        default="",
        help="Bill of Lading / transport document reference (CSV col 38).",
    )
    parser.add_argument(
        "--ucr",
        default="",
        help="UCR / zending reference (CSV col 48).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = process_invoice(
        file_path      = args.input,
        output_dir     = args.output,
        bill_of_lading = args.bl,
        ucr            = args.ucr,
    )

    print(f"\n✅  CSV exported successfully!")
    print(f"   Container No : {result['container_no']}")
    print(f"   Invoice No   : {result['invoice_no']}")
    print(f"   Rows written : {result['row_count']}")
    print(f"   Output file  : {result['output_path']}")


if __name__ == "__main__":
    main()
