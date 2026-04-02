import pytest
from unittest.mock import patch, MagicMock
from src.printer import DymoPrinter


def test_list_dymo_printers_parses_lpstat():
    mock_result = MagicMock()
    mock_result.stdout = (
        "printer DYMO_LabelWriter_550 is idle. enabled since ...\n"
        "printer PDF is idle. enabled since ...\n"
    )
    with patch("subprocess.run", return_value=mock_result):
        result = DymoPrinter.list_dymo_printers()
    assert "DYMO_LabelWriter_550" in result
    assert "PDF" in result


def test_list_dymo_printers_returns_aucune_on_error():
    with patch("subprocess.run", side_effect=Exception("no lpstat")):
        result = DymoPrinter.list_dymo_printers()
    assert result == ["(aucune)"]


def test_list_dymo_printers_returns_aucune_when_empty():
    mock_result = MagicMock()
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        result = DymoPrinter.list_dymo_printers()
    assert result == ["(aucune)"]


def test_print_label_pdf_calls_lp():
    with patch("subprocess.run") as mock_run:
        DymoPrinter.print_label_pdf("/tmp/label.pdf", "DYMO_LabelWriter_550")
    mock_run.assert_called_once_with(
        ["lp", "-d", "DYMO_LabelWriter_550", "/tmp/label.pdf"], check=True)


def test_open_pdf_and_print_macos():
    with patch("src.printer.sys") as mock_sys, patch("subprocess.run") as mock_run:
        mock_sys.platform = "darwin"
        DymoPrinter.open_pdf_and_print("/tmp/a4.pdf")
    mock_run.assert_called_once_with(["open", "/tmp/a4.pdf"], check=True)


def test_open_pdf_and_print_linux():
    with patch("src.printer.sys") as mock_sys, patch("subprocess.run") as mock_run:
        mock_sys.platform = "linux"
        DymoPrinter.open_pdf_and_print("/tmp/a4.pdf")
    mock_run.assert_called_once_with(["xdg-open", "/tmp/a4.pdf"], check=True)
