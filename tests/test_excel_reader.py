import pytest, openpyxl
from src.excel_reader import ExcelReader

SAMPLE = "yves.xlsx"

def test_loads_canonical_file():
    r = ExcelReader(SAMPLE)
    rows = r.all_rows()
    assert len(rows) >= 1
    first = rows[0]
    for key in ("article", "pvente", "ppro", "ppro_htva", "origine", "p_l"):
        assert key in first

def test_search_case_insensitive():
    r = ExcelReader(SAMPLE)
    results = r.search("red bull")
    assert len(results) >= 1
    assert all("red bull" in x["article"].lower() for x in results)

def test_search_empty_returns_all():
    r = ExcelReader(SAMPLE)
    assert len(r.search("")) == len(r.all_rows())

def test_pvente_is_float():
    r = ExcelReader(SAMPLE)
    assert isinstance(r.all_rows()[0]["pvente"], float)

def test_format_price():
    assert ExcelReader.format_price(26.99) == "26,99"
    assert ExcelReader.format_price(1.0)   == "1,00"

def test_search_with_suggestions_returns_both():
    r = ExcelReader(SAMPLE)
    sugg, rows = r.search_with_suggestions("red bull")
    assert len(rows) >= 1
    assert all("red bull" in x["article"].lower() for x in rows)
    assert isinstance(sugg, list)
    assert all(isinstance(s, str) for s in sugg)

def test_search_with_suggestions_empty_query():
    r = ExcelReader(SAMPLE)
    sugg, rows = r.search_with_suggestions("")
    assert sugg == []
    assert len(rows) == len(r.all_rows())

def test_search_with_suggestions_limit():
    r = ExcelReader(SAMPLE)
    sugg, _ = r.search_with_suggestions("red", limit=2)
    assert len(sugg) <= 2

def test_search_with_suggestions_no_match():
    r = ExcelReader(SAMPLE)
    sugg, rows = r.search_with_suggestions("zzznomatch")
    assert sugg == []
    assert rows == []

def test_auto_maps_non_canonical_headers(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nom", "Prix de vente", "Prix pro ttc", "Prix pro htva",
               "TVA", "Code barre", "Pays", "Prix/Litre", "PA"])
    ws.append(["Test Article", 9.99, 8.99, 8.48, 6, 123456, "France", "2,50€/L", 7.0])
    path = str(tmp_path / "test.xlsx")
    wb.save(path)
    r = ExcelReader(path)
    rows = r.all_rows()
    assert rows[0]["article"] == "Test Article"
    assert rows[0]["pvente"]  == 9.99
    assert rows[0]["origine"] == "France"
