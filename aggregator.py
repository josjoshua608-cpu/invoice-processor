"""
aggregator.py
=============
Iterates data rows on the Invoice sheet (from header_row+1 downward)
and aggregates records by HS Code, exactly as the VBA dict logic does:

    * Group by HS Code (numeric, formatted as integer string)
    * Sum: quantity, total_value, net_weight, gross_weight
    * Merge descriptions with "|" separator (no duplicates)
    * Stop when a row whose description contains "SUM" is encountered
      (VBA: If InStr(1, …, "SUM", vbTextCompare) > 0 Then Exit For)
    * Skip rows with blank or non-numeric HS Code values
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


@dataclass
class AggregatedRow:
    hs_code: str
    descriptions: List[str] = field(default_factory=list)
    quantity: float = 0.0
    total_value: float = 0.0
    net_weight: float = 0.0
    gross_weight: float = 0.0

    @property
    def description_str(self) -> str:
        """Return merged description string separated by '|'."""
        return "|".join(self.descriptions)


def _safe_float(val) -> float:
    """Convert a cell value to float, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _cell_val(ws: Worksheet, row: int, col: int):
    """Return raw cell value; '' if col==0 (absent column sentinel)."""
    if col == 0:
        return ""
    return ws.cell(row=row, column=col).value


def _cell_str(ws: Worksheet, row: int, col: int) -> str:
    val = _cell_val(ws, row, col)
    return str(val).strip() if val is not None else ""


def _is_numeric_hs(value) -> bool:
    """Return True if value can be interpreted as a numeric HS code."""
    if value is None:
        return False
    try:
        float(str(value).strip().replace(",", ""))
        return True
    except (ValueError, TypeError):
        return False


def _format_hs(value) -> str:
    """
    Format HS code as an integer string (no decimal point),
    mirroring VBA: Format(CDbl(rawHS), "0")
    """
    try:
        return str(int(float(str(value).strip().replace(",", ""))))
    except (ValueError, TypeError):
        return str(value).strip()


def aggregate(
    ws: Worksheet,
    header_row: int,
    col_hs: int,
    col_desc: int,
    col_qty: int,
    col_val: int,
    col_net: int,
    col_gross: int,
) -> Dict[str, AggregatedRow]:
    """
    Aggregate invoice data rows by HS Code.

    Args:
        ws:         Invoice worksheet.
        header_row: Row index of the column headers.
        col_*:      1-based column indexes (0 = column absent).

    Returns:
        Ordered dict {hs_code_str: AggregatedRow}, preserving first-seen order.
    """
    aggregated: Dict[str, AggregatedRow] = {}

    # Determine last row via col_hs (matches VBA xlUp logic)
    max_row = ws.max_row or 1000

    for r in range(header_row + 1, max_row + 1):
        desc_cell = _cell_str(ws, r, col_desc)

        # VBA stop condition: row description contains "SUM"
        if "sum" in desc_cell.lower():
            logger.debug("SUM row encountered at row %d – stopping iteration.", r)
            break

        raw_hs = _cell_val(ws, r, col_hs)

        # Skip rows with blank or non-numeric HS code
        if not _is_numeric_hs(raw_hs):
            continue

        hs_key = _format_hs(raw_hs)

        qty   = _safe_float(_cell_val(ws, r, col_qty))
        val   = _safe_float(_cell_val(ws, r, col_val))
        net   = _safe_float(_cell_val(ws, r, col_net))
        gross = _safe_float(_cell_val(ws, r, col_gross))

        if hs_key not in aggregated:
            agg = AggregatedRow(hs_code=hs_key)
            if desc_cell:
                agg.descriptions.append(desc_cell)
            agg.quantity    = qty
            agg.total_value = val
            agg.net_weight  = net
            agg.gross_weight = gross
            aggregated[hs_key] = agg
            logger.debug("New HS key: %s  desc=%r", hs_key, desc_cell)
        else:
            agg = aggregated[hs_key]
            # Merge description only if not already present (VBA: InStr check)
            if desc_cell and desc_cell not in agg.descriptions:
                agg.descriptions.append(desc_cell)
            agg.quantity     += qty
            agg.total_value  += val
            agg.net_weight   += net
            agg.gross_weight += gross
            logger.debug("Merged HS key: %s  running_val=%.2f", hs_key, agg.total_value)

    logger.info("Aggregation complete: %d unique HS codes found.", len(aggregated))
    return aggregated
