# CandyStock — Label & Poster Printer

## Architecture
- Desktop Python app (CustomTkinter GUI + PyInstaller `.exe`)
- Prints to Dymo via SumatraPDF (bundled) / win32print
- Forked from GoForPrize — desktop .exe only, no web app

## Commands
- `python app.py` — run locally
- `pyinstaller CandyStock.spec --clean --noconfirm` — build .exe
- `python -m pytest tests/` — run tests

## Desktop App
- Python 3.x + CustomTkinter
- Entry point: `app.py`, UI: `ui/main_window.py`
- Build: `pyinstaller CandyStock.spec`
- Config: `config.json`, history: `history.json`
- Product table: ttk.Treeview (handles 5000+ rows natively)
- Product keys in UI include row index `(article, pvente, idx)` — needed for duplicate Excel rows
- Auto-detect printer prefers "dymo"/"label" in name
- Preview and PDF use DIFFERENT code — fix BOTH when changing layout
- `.exe` build: GitHub Actions on push to `main`; also `gh workflow run "Build Windows EXE"`

## Print Formats
- **Dymo labels**: 89mm × 36mm **landscape** (DO NOT change to portrait)
- **A5 poster**: Content on LEFT HALF of A4 portrait page (blank paper)
  - Page size: A4 portrait (210×297mm)
  - Content area: left 105mm only
  - No header zone — full height available
  - No pre-printed background

## Dymo Printing
- Label PDF: 89mm × 36mm landscape
- SumatraPDF bundled in .exe for silent printing (no window flash)
- Windows: STARTUPINFO(SW_HIDE) + CREATE_NO_WINDOW flags
- Windows driver MUST be set to **99012 Large Address** (89×36mm)
- macOS/CUPS: `media=Custom.36x89mm`, `orientation-requested=4`, `fit-to-page`
- ALWAYS test on real Dymo hardware before shipping

## Customer
- Candy Stock — Belgian wholesale (currency EUR, locale fr-BE)
- Products: sweets, chocolates, drinks
- Blank A4 paper (no pre-printed layout)
- Dymo LabelWriter 550 for price labels (89×36mm, label type 99012 Large Address)
- Windows PC with Dymo (runs .exe)

## Deployment
- GitHub Actions builds .exe on push to `main` → releases at `latest` tag
- Download: GitHub releases page
