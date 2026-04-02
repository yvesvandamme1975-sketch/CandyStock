import json, pytest
from src.history_manager import HistoryManager

P = {"article": "Red Bull 24x25cl", "pvente": 26.99,
     "ppro": 25.99, "ppro_htva": 24.52,
     "origine": "Belgique", "p_l": "4,50€/L"}

def test_add_and_list(tmp_path):
    hm = HistoryManager(str(tmp_path / "history.json"))
    hm.add(P, fmt="label")
    entries = hm.list()
    assert len(entries) == 1
    assert entries[0]["article"] == "Red Bull 24x25cl"
    assert entries[0]["format"] == "label"
    assert "timestamp" in entries[0]

def test_most_recent_first(tmp_path):
    hm = HistoryManager(str(tmp_path / "history.json"))
    hm.add({**P, "article": "First"},  fmt="label")
    hm.add({**P, "article": "Second"}, fmt="a4")
    entries = hm.list()
    assert entries[0]["article"] == "Second"

def test_persists_across_reload(tmp_path):
    path = str(tmp_path / "history.json")
    hm = HistoryManager(path)
    hm.add(P, fmt="a4")
    hm2 = HistoryManager(path)
    assert len(hm2.list()) == 1

def test_max_100_entries(tmp_path):
    hm = HistoryManager(str(tmp_path / "history.json"))
    for i in range(110):
        hm.add({**P, "article": f"Art {i}"}, fmt="label")
    assert len(hm.list()) == 100
    assert hm.list()[0]["article"] == "Art 109"
