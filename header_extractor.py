"""
header_extractor.py
===================
Scans the first 50 rows (up to 20 columns) of the Invoice sheet to
extract the four header-level fields:

    invoice_no    – cell after "Invoice No"
    container_no  – cell after "Reference Number"
    currency      – exact cell value of USD / EUR / INR / CNY
    country       – cell after a "country" label (excluding
                    "delivery" and "destination" context words)

All logic mirrors the original VBA macro exactly.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

CURRENCIES = {"USD", "EUR", "INR", "CNY"}
SCAN_ROWS = 50
SCAN_COLS = 20


class HeaderExtractorError(Exception):
    """Raised when a mandatory header field cannot be found."""


def _cell_str(ws: Worksheet, row: int, col: int) -> str:
    """Return cell value as a stripped string, or '' if empty/None."""
    val = ws.cell(row=row, column=col).value
    return str(val).strip() if val is not None else ""


def _next_nonempty(ws: Worksheet, row: int, col: int) -> str:
    """
    Return the value from col+1 if non-empty, else col+2.
    Mirrors the VBA pattern used for every label→value lookup.
    """
    v1 = _cell_str(ws, row, col + 1)
    if v1:
        return v1
    return _cell_str(ws, row, col + 2)


def extract_headers(
    ws: Worksheet,
) -> Tuple[str, str, str, str]:
    """
    Scan the Invoice sheet and return (invoice_no, container_no,
    currency, country_of_origin).

    Scans rows 1–50, columns 1–20 (identical bounds to the VBA macro).

    Args:
        ws: The Invoice worksheet.

    Returns:
        4-tuple of strings (all may be '' if not found).
    """
    invoice_no: str = ""
    container_no: str = ""
    currency: str = ""
    country: str = ""

    for rr in range(1, SCAN_ROWS + 1):
        for cc in range(1, SCAN_COLS + 1):
            cell_val = _cell_str(ws, rr, cc)
            cell_lower = cell_val.lower()

            # --- Currency (exact match) ---
            if not currency and cell_val in CURRENCIES:
                currency = cell_val
                logger.debug("Currency '%s' found at (%d,%d)", currency, rr, cc)

            # --- Invoice Number ---
            if not invoice_no and "invoice no" in cell_lower:
                invoice_no = _next_nonempty(ws, rr, cc)
                logger.debug("Invoice No '%s' found at (%d,%d)", invoice_no, rr, cc)

            # --- Container / Reference Number ---
            if not container_no and "reference number" in cell_lower:
                container_no = _next_nonempty(ws, rr, cc)
                logger.debug(
                    "Container No '%s' found at (%d,%d)", container_no, rr, cc
                )

            # --- Country of Origin ---
            # Must contain "country", must NOT contain "delivery" or "destination"
            if (
                not country
                and "country" in cell_lower
                and "delivery" not in cell_lower
                and "destination" not in cell_lower
            ):
                country = _next_nonempty(ws, rr, cc)
                logger.debug(
                    "Country of Origin '%s' found at (%d,%d)", country, rr, cc
                )

        # Early exit once all four are found
        if invoice_no and container_no and currency and country:
            break

    # Warnings for missing fields (not fatal – some invoices may omit fields)
    if not invoice_no:
        logger.warning("Invoice number not found in first %d rows.", SCAN_ROWS)
    if not container_no:
        logger.warning("Container/Reference number not found in first %d rows.", SCAN_ROWS)
    if not currency:
        logger.warning("Currency not found. Defaulting to empty string.")
    if not country:
        logger.warning("Country of origin not found.")

    return invoice_no, container_no, currency, country
