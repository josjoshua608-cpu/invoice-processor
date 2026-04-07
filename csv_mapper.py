"""
csv_mapper.py
=============
Maps processed invoice data into a pandas DataFrame with EXACTLY 82
columns, in the exact order defined by the CSV template.

Column mapping (VBA Input sheet → CSV output):
    col E  → Artikelcode       (col 2)   ← HS Code
    col F  → Goederenomschrijving (col 4) ← Description
    col G  → Verpakking        (col 5)   ← Package unit ("PK")
    col H  → Aantal            (col 6)   ← Package count (from packing matcher)
    col I  → Bruto (kg)        (col 8)   ← Gross weight
    col J  → Netto (kg)        (col 9)   ← Net weight
    col K  → Land van oorsprong (col 14) ← Country of origin
    col L  → Prijs van goederen (col 28) ← Total value
    col M  → Valuta (col 29)             ← Currency

Fixed/default values copied from the CSV template:
    Volgnr                    → row sequence (1, 2, 3…)
    Goederencode              → same as Artikelcode (HS code)
    Merken en nummers         → "NM"
    Aanvullende eenheden      → " "  (single space)
    Gevraagde regeling        → "40"
    Voorafgaande regeling     → "00"
    Type (col 13)             → " "  (single space)
    Preferentiële oorsprong   → " "
    Contingent                → " "
    Communautaire preferentiële → "100"
    Waarderingsmethode        → "1"
    Waarderingsindicator      → "0001"
    Kostenfactor (col 30)     → "0"
    Bedrag (col 31)           → "0"
    Valuta (col 32)           → "0"
    Containernummer (col 33)  → container_no
    col 37 (Type)             → "N705"
    col 38 (Nummer)           → bill_of_lading (from container_no context – populated
                                 from col 38 in template sample; defaults to "")
    col 39 (Artikelnummer)    → "1"
    col 47 (Type)             → "N935"
    col 48 (Nummer)           → ucr  (from packing sheet or left empty)
    All other columns         → ""

The mapping uses the EXACT column order extracted from the template CSV.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd

from aggregator import AggregatedRow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EXACT 82-column header list extracted from EMCU8867382-3.csv (latin-1)
# ---------------------------------------------------------------------------
CSV_COLUMNS: List[str] = [
    "Volgnr",                        # 1
    "Artikelcode",                   # 2  ← HS Code
    "Goederencode",                  # 3  ← HS Code (duplicate)
    "Goederenomschrijving",          # 4  ← Description
    "Verpakking",                    # 5  ← "PK"
    "Aantal",                        # 6  ← Package count
    "Merken en nummers",             # 7  ← "NM"
    "Bruto (kg)",                    # 8  ← Gross weight
    "Netto (kg)",                    # 9  ← Net weight
    "Aanvullende eenheden",          # 10 ← " "
    "Gevraagde regeling",            # 11 ← "40"
    "Voorafgaande regeling",         # 12 ← "00"
    "Type",                          # 13 ← " "
    "Land van oorsprong",            # 14 ← Country
    "Preferentiële oorsprong",       # 15 ← " "
    "Contingent",                    # 16 ← " "
    "Communautaire preferentiële",   # 17 ← "100"
    "Waarderingsmethode",            # 18 ← "1"
    "Waarderingsindicator",          # 19 ← "0001"
    "Middelcode",                    # 20
    "Maatstafwaarde",                # 21
    "Maatstafhoeveelheid",           # 22
    "Maatstaf",                      # 23
    "Belastingbedrag",               # 24
    "Tarief",                        # 25
    "Verschuldigd belastingbedrag",  # 26
    "Betaalwijze",                   # 27
    "Prijs van goederen",            # 28 ← Total value
    "Valuta",                        # 29 ← Currency
    "Kostenfactor",                  # 30 ← "0"
    "Bedrag",                        # 31 ← "0"
    "Valuta",                        # 32 ← "0"  (second Valuta column)
    "Containernummer",               # 33 ← container_no
    "Artikelnummer",                 # 34
    "Type",                          # 35
    "Nummer",                        # 36
    "Type",                          # 37 ← "N705"
    "Nummer",                        # 38 ← bill_of_lading / reference
    "Artikelnummer",                 # 39 ← "1"
    "Code",                          # 40
    "Beschrijving",                  # 41
    "Type",                          # 42
    "Nummer",                        # 43
    "Type",                          # 44
    "Nummer",                        # 45
    "Houder",                        # 46
    "Type",                          # 47 ← "N935"
    "Nummer",                        # 48 ← UCR / zending reference
    "Artikelnummer",                 # 49
    "Geldigheidsdatum",              # 50
    "Naam autoriteit van afgifte",   # 51
    "Aantal",                        # 52
    "Maatstaf",                      # 53
    "Bedrag",                        # 54
    "Valuta",                        # 55
    "AEO partij",                    # 56
    "Rol",                           # 57
    "In-/Verkoop",                   # 58
    "Verkoopprijs",                  # 59
    "Valuta",                        # 60
    "Koper eori",                    # 61
    "Koper naam",                    # 62
    "Koper straat en nr.",           # 63
    "Koper postcode",                # 64
    "Koper plaats",                  # 65
    "Koper land",                    # 66
    "Verkoper eori",                 # 67
    "Verkoper naam",                 # 68
    "Verkoper straat en nr.",        # 69
    "Verkoper postcode",             # 70
    "Verkoper plaats",               # 71
    "Verkoper land",                 # 72
    "Exporteur eori",                # 73
    "Exporteur naam",                # 74
    "Exporteur straat en nr.",       # 75
    "Exporteur postcode",            # 76
    "Exporteur plaats",              # 77
    "Exporteur land",                # 78
    "UCR/Zendingrefentie",           # 79
    "Aard van transactie",           # 80
    "Land van verzending",           # 81
    "Land van bestemming",           # 82
]

assert len(CSV_COLUMNS) == 82, f"Column count mismatch: {len(CSV_COLUMNS)}"


def build_dataframe(
    aggregated: Dict[str, AggregatedRow],
    pkg_totals: Dict[str, float],
    invoice_no: str,
    container_no: str,
    currency: str,
    country: str,
    bill_of_lading: str = "",
    ucr: str = "",
) -> pd.DataFrame:
    """
    Build the 82-column output DataFrame from aggregated invoice data.

    Args:
        aggregated:     {hs_code: AggregatedRow} from aggregator.
        pkg_totals:     {hs_code: total_packages} from packing_matcher.
        invoice_no:     Invoice number string.
        container_no:   Container / reference number.
        currency:       Currency code (USD/EUR/INR/CNY).
        country:        Country of origin code.
        bill_of_lading: BL / transport document reference (col 38).
        ucr:            UCR / zending reference (col 48).

    Returns:
        pandas DataFrame with EXACTLY 82 columns.
    """
    rows: List[dict] = []
    sequence = 1

    for hs_code, agg in aggregated.items():
        pkg_count = pkg_totals.get(hs_code, 0)

        # Build a row dict keyed by POSITION (0-indexed) to handle duplicate
        # column names safely, then we'll assign via positional list
        row_values: List = [""] * 82

        # col 1  – Volgnr (sequence number)
        row_values[0]  = sequence

        # col 2  – Artikelcode (HS Code)
        row_values[1]  = hs_code

        # col 3  – Goederencode (HS Code, again – matches template)
        row_values[2]  = hs_code

        # col 4  – Goederenomschrijving (Description)
        row_values[3]  = agg.description_str

        # col 5  – Verpakking ("PK")
        row_values[4]  = "PK"

        # col 6  – Aantal (package count from packing matcher)
        row_values[5]  = int(pkg_count) if pkg_count == int(pkg_count) else pkg_count

        # col 7  – Merken en nummers ("NM")
        row_values[6]  = "NM"

        # col 8  – Bruto (kg) (gross weight)
        row_values[7]  = agg.gross_weight

        # col 9  – Netto (kg) (net weight)
        row_values[8]  = agg.net_weight

        # col 10 – Aanvullende eenheden (" ")
        row_values[9]  = " "

        # col 11 – Gevraagde regeling ("40")
        row_values[10] = "40"

        # col 12 – Voorafgaande regeling ("00")
        row_values[11] = "00"

        # col 13 – Type (" ")
        row_values[12] = " "

        # col 14 – Land van oorsprong (country of origin)
        row_values[13] = country

        # col 15 – Preferentiële oorsprong (" ")
        row_values[14] = " "

        # col 16 – Contingent (" ")
        row_values[15] = " "

        # col 17 – Communautaire preferentiële ("100")
        row_values[16] = "100"

        # col 18 – Waarderingsmethode ("1")
        row_values[17] = "1"

        # col 19 – Waarderingsindicator ("0001")
        row_values[18] = "0001"

        # col 20–27 → "" (empty)

        # col 28 – Prijs van goederen (total value)
        row_values[27] = agg.total_value

        # col 29 – Valuta (currency)
        row_values[28] = currency

        # col 30 – Kostenfactor ("0")
        row_values[29] = "0"

        # col 31 – Bedrag ("0")
        row_values[30] = "0"

        # col 32 – Valuta (second, "0" per template)
        row_values[31] = "0"

        # col 33 – Containernummer
        row_values[32] = container_no

        # col 34 – Artikelnummer → ""
        # col 35 – Type → ""
        # col 36 – Nummer → ""

        # col 37 – Type ("N705")
        row_values[36] = "N705"

        # col 38 – Nummer (bill of lading / transport doc reference)
        row_values[37] = bill_of_lading

        # col 39 – Artikelnummer ("1")
        row_values[38] = "1"

        # col 40–46 → ""

        # col 47 – Type ("N935")
        row_values[46] = "N935"

        # col 48 – Nummer (UCR)
        row_values[47] = ucr

        # col 49–82 → "" (already empty from initialisation)

        rows.append(row_values)
        sequence += 1

    # Build DataFrame using integer column positions to handle duplicate names
    df_raw = pd.DataFrame(rows, columns=list(range(82)))
    df_raw.columns = CSV_COLUMNS  # assign canonical names

    # Safety check: enforce column count
    assert len(df_raw.columns) == 82, (
        f"CRITICAL: output DataFrame has {len(df_raw.columns)} columns, expected 82."
    )

    logger.info(
        "DataFrame built: %d data rows × %d columns.", len(df_raw), len(df_raw.columns)
    )
    return df_raw
