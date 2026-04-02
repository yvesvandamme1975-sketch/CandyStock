import json, os, pytest
from src.config_manager import ConfigManager

def test_defaults_when_no_file(tmp_path):
    cm = ConfigManager(config_path=str(tmp_path / "config.json"))
    assert cm.get("label_size") == "89x36"
    assert cm.get("usb_printer") == ""
    assert cm.get("last_excel_path") == ""
    assert cm.get("printer_type") is None
    assert cm.get("network_ip") is None

def test_save_and_reload(tmp_path):
    path = str(tmp_path / "config.json")
    cm = ConfigManager(config_path=path)
    cm.set("usb_printer", "DYMO_LabelWriter_550")
    cm.save()
    cm2 = ConfigManager(config_path=path)
    assert cm2.get("usb_printer") == "DYMO_LabelWriter_550"

def test_get_nonexistent_key_returns_none(tmp_path):
    cm = ConfigManager(config_path=str(tmp_path / "config.json"))
    assert cm.get("nonexistent") is None
