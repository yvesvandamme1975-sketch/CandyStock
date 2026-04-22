# CandyStock — Label & Poster Printer

## Architecture
- Desktop Python app (CustomTkinter GUI + PyInstaller `.exe`)
- Prints to Dymo via SumatraPDF (bundled) / win32print
- Forked from GoForPrize — desktop .exe only, no web app
- Entry point: `app.py`, UI: `ui/main_window.py`

## Commands
- `python app.py` — run locally
- `pyinstaller CandyStock.spec --clean --noconfirm` — build .exe
- `python -m pytest tests/` — run tests

## Key Files
| File | Purpose |
|------|---------|
| `ui/main_window.py` | Main GUI — product table, preview canvas, print actions |
| `src/pdf_generator.py` | PDF generation for labels (89x36mm) and A5 posters |
| `src/excel_reader.py` | Excel parsing, EAN detection, price normalization |
| `src/column_mapper.py` | Auto-maps Excel headers to internal field names |
| `src/text_cleaner.py` | Brand name corrections for article names |
| `src/printer.py` | Dymo/SumatraPDF printing (Windows + macOS) |
| `src/config_manager.py` | Label sizes, printer settings |
| `CandyStock.spec` | PyInstaller config — bundles barcode, fitz, tkinterdnd2 |

## Product Data Fields
- Only **Article Name** + **Price HTVA** displayed on labels/posters
- No PPHT, PPTTC, Origin, or Price/litre shown (wholesale simplification)
- EAN barcode auto-detected from Excel (8 or 13 digits, handles 14-digit with leading 0)

## Column Mapper (`src/column_mapper.py`)
- 2-pass: exact/substring match, then fuzzy (difflib, cutoff=0.75)
- Supports French AND English headers (e.g. "Product Name", "Price Without VAT", "Barcode")
- REQUIRED fields: `article`, `pvente` only
- EAN fallback: if no column maps to EAN, scans ALL row values for 8/13-digit patterns
- Watch for substring false positives (e.g. "vente" matching unrelated columns)

## Print Formats

### Dymo Labels (89 x 36mm landscape)
- Article: 11pt Helvetica-Bold at top (1-2 lines, wraps if needed)
- Price: 18pt centered between article and barcode
- Barcode: module_height=8, font_size=5, width=30mm, at bottom
- Margin: 3mm
- **DO NOT change to portrait orientation**
- SumatraPDF bundled in .exe for silent printing
- Windows driver MUST be set to **99012 Large Address** (89x36mm)

### A5 Poster (left half of A4 landscape)
- Page: A4 **landscape** (297x210mm), content on LEFT half (148.5x210mm)
- Article: 58pt (shrinks to 48/36pt for 2-3 lines), 20mm from top
- Price: 100pt (auto-shrinks to fit width), vertically centered
- Barcode: module_height=12, width=60mm, 35mm from bottom
- Logo: 80mm wide, 10mm from bottom
- Blank paper — no pre-printed background, no header zone

## Preview Canvas vs PDF
- Preview (`main_window.py`) and PDF (`pdf_generator.py`) use DIFFERENT code
- **Fix BOTH** when changing layout — positions must match proportionally
- Preview uses proportional values (% of card dimensions) to match PDF mm positions
- Label preview: font sizes = `lh * 0.12` (title), `lh * 0.19` (price)
- A5 preview: font sizes = `a5h * 0.065` (title), `a5h * 0.11` (price, auto-shrinks)
- Barcode in preview: `_draw_barcode_on_canvas()` returns item ID for bbox positioning

## Barcode Support
- Library: `python-barcode==0.16.1` with PIL ImageWriter
- Supports EAN-13 and EAN-8
- PyInstaller bundling: `collect_all('barcode')` in spec + explicit hiddenimports
- `_make_barcode_image()` catches all exceptions, returns None on failure
- `_HAS_BARCODE` flag — if False, all barcodes silently disabled

## Product Table
- ttk.Treeview (handles 5000+ rows natively)
- 3 columns: checkbox, article, prix HTVA
- Product keys include row index `(article, pvente, idx)` for duplicate rows

## Dymo Printing Details
- macOS/CUPS: `media=Custom.36x89mm`, `orientation-requested=4`, `fit-to-page`
- Windows: SumatraPDF with `-print-settings fit` (preferred)
- Fallback chain: SumatraPDF → win32api.ShellExecute → PowerShell → os.startfile
- `win32api.ShellExecute("printto")` is ASYNC — batch print needs unique temp files
- `os.startfile("print")` ignores printer_name — uses default printer only
- **Label print success is SILENT** — do NOT add `messagebox.showinfo` after `print_label_pdf()`. Customer needs to print dozens per session without clicking OK. Errors (`messagebox.showerror`) stay. Applies to both `_print_label` and `_batch_print_labels` in `ui/main_window.py`.

## Customer
- Candy Stock — Belgian wholesale (currency EUR, locale fr-BE)
- Products: sweets, chocolates, drinks
- Blank A4 paper (no pre-printed layout)
- Dymo LabelWriter 550 for price labels
- Windows PC with Dymo (runs .exe)
- Labels show "€/HTVA" (price without VAT)

## Deployment
- GitHub Actions builds .exe on push to `main` → releases at `latest` tag
- Build triggers: changes to `app.py`, `src/**`, `ui/**`, `assets/**`, `requirements.txt`, `CandyStock.spec`, workflow file
- Download: GitHub releases page (`latest` tag)
- Version indicator in window title (e.g. "v2.1") for debugging build issues
