import os, pytest
from src.pdf_generator import PdfGenerator

P = {"article": "Red Bull 24x25cl", "pvente": 26.99,
     "ppro": 25.99, "ppro_htva": 24.52,
     "origine": "Belgique", "p_l": "4,50€/L"}

def test_generates_pdf(tmp_path):
    out = str(tmp_path / "poster.pdf")
    PdfGenerator.generate_a4(P, out, logo_path=None)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000

def test_returns_path(tmp_path):
    out = str(tmp_path / "p.pdf")
    assert PdfGenerator.generate_a4(P, out, logo_path=None) == out

def test_generates_with_logo(tmp_path):
    # create a tiny 1x1 PNG as dummy logo
    from PIL import Image
    logo = str(tmp_path / "logo.png")
    Image.new("RGB", (10, 10), color="red").save(logo)
    out = str(tmp_path / "poster_logo.pdf")
    PdfGenerator.generate_a4(P, out, logo_path=logo)
    assert os.path.exists(out)
