import pytest
from src.column_mapper import ColumnMapper

def test_exact_canonical_headers():
    headers = ["article", "Pvente", "Ppro", "PPro HTVA", "ORIGINE", "P/L"]
    m = ColumnMapper.auto_map(headers)
    assert m["article"]   == "article"
    assert m["pvente"]    == "Pvente"
    assert m["ppro"]      == "Ppro"
    assert m["ppro_htva"] == "PPro HTVA"
    assert m["origine"]   == "ORIGINE"
    assert m["p_l"]       == "P/L"

def test_case_insensitive():
    headers = ["ARTICLE", "PVENTE", "PPRO", "PPRO HTVA"]
    m = ColumnMapper.auto_map(headers)
    assert m["article"] == "ARTICLE"
    assert m["pvente"]  == "PVENTE"

def test_synonym_match():
    headers = ["Nom", "Prix de vente", "Prix pro ttc", "Prix pro htva"]
    m = ColumnMapper.auto_map(headers)
    assert m["article"]   == "Nom"
    assert m["pvente"]    == "Prix de vente"
    assert m["ppro"]      == "Prix pro ttc"
    assert m["ppro_htva"] == "Prix pro htva"

def test_fuzzy_match():
    headers = ["artikle", "Pventes", "Ppros", "PPro HTVAS"]
    m = ColumnMapper.auto_map(headers)
    assert m.get("article") == "artikle"

def test_unresolved_returns_none():
    m = ColumnMapper.auto_map(["foo", "bar"])
    assert m.get("article") is None

def test_missing_required_detected():
    missing = ColumnMapper.missing_required(ColumnMapper.auto_map(["foo"]))
    assert "article" in missing
    assert "pvente"  in missing
