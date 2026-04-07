# Invoice Processor — Python Backend System

Converts invoice Excel files into the **exact 82-column** Dutch customs CSV
format, replicating all VBA macro logic.

---

## Folder Structure

```
invoice_processor/
│
├── main.py              # Orchestrator / CLI entry point
├── file_loader.py       # Workbook loading + sheet detection
├── header_extractor.py  # Invoice No, Container No, Currency, Country
├── column_detector.py   # Dynamic header-row + column-position detection
├── aggregator.py        # HS Code grouping, summing, description merging
├── packing_matcher.py   # Packing list matching → package totals
├── csv_mapper.py        # Maps data into 82-column DataFrame
├── exporter.py          # CSV file writer (disk / bytes / string)
│
├── requirements.txt
├── README.md
└── output/              # Created automatically on first run
```

---

## Requirements

- Python 3.9 or later
- pip packages listed in `requirements.txt`

---

## Setup

```bash
# 1. Clone / copy the invoice_processor/ folder to your machine

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running Locally

### Basic usage
```bash
python main.py --input path/to/invoice.xlsx
```

### With explicit output directory
```bash
python main.py --input invoice.xlsx --output ./my_output
```

### With Bill of Lading and UCR references
```bash
python main.py \
    --input invoice.xlsx \
    --output ./output \
    --bl EGLV143656438208 \
    --ucr NE34554B-FBA15LCL0MXQ
```

### Verbose (DEBUG) logging
```bash
python main.py --input invoice.xlsx --verbose
```

---

## Expected Excel Structure

The input Excel file must:

1. Have a sheet whose name contains **"Invoice"** (case-insensitive)
2. Have a second sheet used as the **Packing List** (or any sheet whose
   name contains "pack")
3. Invoice sheet must include within the first 50 rows / 20 columns:
   - A cell containing **"Invoice No"**
   - A cell containing **"Reference Number"**
   - A cell containing a currency: **USD / EUR / INR / CNY**
   - A cell containing **"country"** (not delivery/destination)
4. Invoice sheet must have a header row (within first 40 rows) containing:
   - **HS Code** (cell with both "HS" and "Code")
   - **Description of Goods**
   - **Quantity**
   - **Total Value**
   - **Total Net**
   - **Total Gross**
5. Packing List sheet: description in **column B**, package count in **column G**

---

## Output

- File written to `<output_dir>/<container_no>.csv`
- If the file already exists: `<container_no>_2.csv`, `_3.csv`, etc.
- Always **exactly 82 columns** in the order defined by the template

---

## CSV Column Mapping

| CSV Column (position) | Dutch name                  | Source                     |
|-----------------------|-----------------------------|----------------------------|
| 1                     | Volgnr                      | Row sequence (1, 2, 3…)    |
| 2                     | Artikelcode                 | HS Code                    |
| 3                     | Goederencode                | HS Code                    |
| 4                     | Goederenomschrijving        | Description (pipe-merged)  |
| 5                     | Verpakking                  | "PK" (fixed)               |
| 6                     | Aantal                      | Package count (packing list)|
| 7                     | Merken en nummers           | "NM" (fixed)               |
| 8                     | Bruto (kg)                  | Gross weight               |
| 9                     | Netto (kg)                  | Net weight                 |
| 10                    | Aanvullende eenheden        | " " (space)                |
| 11                    | Gevraagde regeling          | "40" (fixed)               |
| 12                    | Voorafgaande regeling       | "00" (fixed)               |
| 14                    | Land van oorsprong          | Country of origin          |
| 17                    | Communautaire preferentiële | "100" (fixed)              |
| 18                    | Waarderingsmethode          | "1" (fixed)                |
| 19                    | Waarderingsindicator        | "0001" (fixed)             |
| 28                    | Prijs van goederen          | Total value                |
| 29                    | Valuta                      | Currency                   |
| 33                    | Containernummer             | Container No               |
| 37                    | Type                        | "N705" (fixed)             |
| 38                    | Nummer                      | Bill of Lading (--bl arg)  |
| 39                    | Artikelnummer               | "1" (fixed)                |
| 47                    | Type                        | "N935" (fixed)             |
| 48                    | Nummer                      | UCR (--ucr arg)            |
| all others            | —                           | "" (empty)                 |

---

## Using as a Python API (for SaaS integration)

```python
from main import process_invoice
from exporter import export_to_bytes, export_to_string

# Returns a dict with output_path, container_no, invoice_no, row_count, df
result = process_invoice(
    file_path="invoice.xlsx",
    output_dir="output",
    bill_of_lading="EGLV143656438208",
    ucr="NE34554B-FBA15LCL0MXQ",
)

# Get CSV as bytes for HTTP streaming
csv_bytes = export_to_bytes(result["df"])

# Get CSV as string
csv_str = export_to_string(result["df"])
```

### FastAPI example
```python
from fastapi import FastAPI, UploadFile
from fastapi.responses import Response
import tempfile, shutil
from main import process_invoice
from exporter import export_to_bytes

app = FastAPI()

@app.post("/process-invoice")
async def process(file: UploadFile):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    result = process_invoice(tmp_path)
    csv_bytes = export_to_bytes(result["df"])

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{result["container_no"]}.csv"'
        },
    )
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| "Invoice sheet not found" | Sheet name doesn't contain "Invoice" | Rename the sheet or check spelling |
| HS Code column not detected | Header uses different spelling | Check that header cell contains both "HS" and "Code" |
| All package counts are 0 | Packing list descriptions don't match invoice | Ensure descriptions are identical (case-insensitive exact match) |
| UnicodeEncodeError on export | Non-latin characters in data | Modify `DEFAULT_ENCODING` in `exporter.py` to `"utf-8-sig"` |
| Empty container_no | "Reference Number" label not found | Check spelling in the invoice header area |
