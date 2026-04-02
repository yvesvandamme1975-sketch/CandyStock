import io, os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from src.text_cleaner import clean_article
from src.excel_reader import ExcelReader

PAGE_W, PAGE_H = A4   # portrait: 210 × 297 mm
MARGIN = 10 * mm


class PdfGenerator:
    # A5 content on left half of A4 portrait (blank paper)
    A5_W_MM = 105   # half of 210mm
    A5_H_MM = 148.5 # half of 297mm (but we use full page height)

    @staticmethod
    def generate_a4(product: dict, output_path: str,
                    logo_path=None) -> str:
        """Generate A5-sized content on the left half of an A4 portrait page.

        Blank paper — all content is printed (no pre-printed background).
        Content fits in the left 105mm of the A4 page.
        """
        article   = clean_article(str(product.get("article", "")).strip())
        pvente    = float(product.get("pvente",    0))
        ppro      = float(product.get("ppro",      0))
        ppro_htva = float(product.get("ppro_htva", 0))
        origine   = str(product.get("origine", "")).strip()
        p_l       = str(product.get("p_l", "")).strip()

        price_str = f"{pvente:.2f}".replace(".", ",") + "\u20ac"
        ppht_str  = f"{ppro_htva:.2f}".replace(".", ",")
        ppttc_str = f"{ppro:.2f}".replace(".", ",")

        page_w, page_h = A4   # 595.28 × 841.89 pt (210 × 297 mm)
        half_w  = page_w / 2  # left A5 zone = 105mm
        margin  = 10 * mm
        cx      = half_w / 2  # centre of left half

        c = rl_canvas.Canvas(output_path, pagesize=A4)
        c.setFillColor(colors.black)

        # ── Article name ── top of left half, centred ────────────────
        max_w     = half_w - 2 * margin
        font_size = 32
        line_gap  = font_size * 1.2
        art_top   = page_h - 20 * mm

        if stringWidth(article, "Helvetica-Bold", font_size) <= max_w:
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(cx, art_top, article)
        else:
            while font_size > 14:
                words = article.split()
                line1 = ""
                for word in words:
                    test = (line1 + " " + word).strip()
                    if stringWidth(test, "Helvetica-Bold", font_size) <= max_w:
                        line1 = test
                    else:
                        break
                line2 = article[len(line1):].strip()
                if (line1 and
                        stringWidth(line1, "Helvetica-Bold", font_size) <= max_w and
                        stringWidth(line2, "Helvetica-Bold", font_size) <= max_w):
                    break
                font_size -= 1
            line_gap = font_size * 1.2
            words = article.split()
            line1 = ""
            for word in words:
                test = (line1 + " " + word).strip()
                if stringWidth(test, "Helvetica-Bold", font_size) <= max_w:
                    line1 = test
                else:
                    break
            line2 = article[len(line1):].strip()
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(cx, art_top, line1)
            c.drawCentredString(cx, art_top - line_gap, line2)

        # ── Price ── large, centred in left half ─────────────────────
        c.setFont("Helvetica-Bold", 64)
        c.drawCentredString(cx, page_h / 2, price_str)

        # ── Price per litre ── bottom-left of left half ──────────────
        if p_l:
            c.setFont("Helvetica", 14)
            c.drawString(margin, margin + 20 * mm,
                         ExcelReader.format_price_per_litre(p_l))

        # ── Origine ── bottom-right of left half ─────────────────────
        if origine:
            c.setFont("Helvetica", 14)
            c.drawRightString(half_w - margin, margin + 20 * mm,
                              f"Origine : {origine}")

        # ── Pro prices ── bottom of left half ────────────────────────
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(half_w - margin, margin + 8 * mm,
                          f"PPHT {ppht_str}    PPTTC {ppttc_str}")

        c.save()
        return output_path

    @staticmethod
    def generate_label(product: dict, output_path: str,
                       logo_path, width_mm: float = 89,
                       height_mm: float = 36) -> str:
        """Generate a label-sized PDF for Dymo LabelWriter 550."""
        article   = clean_article(str(product.get("article", "")).strip())
        pvente    = float(product.get("pvente",    0))
        ppro      = float(product.get("ppro",      0))
        ppro_htva = float(product.get("ppro_htva", 0))

        price_str = f"{pvente:.2f}".replace(".", ",") + "\u20ac"
        ppht_str  = f"{ppro_htva:.2f}".replace(".", ",")
        ppttc_str = f"{ppro:.2f}".replace(".", ",")
        pro_str   = f"PPHT {ppht_str}   PPTTC {ppttc_str}"

        page_w = width_mm  * mm
        page_h = height_mm * mm
        margin = 3 * mm

        # Golden-ratio font stack (8 → 13 → 21 pt)
        RATIO   = 1.61
        f_pro   = 8
        f_title = round(f_pro   * RATIO)   # 13
        f_price = round(f_title * RATIO)   # 21

        c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))

        # ── Article title — top-left, bold, up to 2 lines ──────────
        max_text_w = page_w - 2 * margin
        c.setFont("Helvetica-Bold", f_title)
        c.setFillColor(colors.black)

        full_w = stringWidth(article, "Helvetica-Bold", f_title)
        cx = page_w / 2
        if full_w <= max_text_w:
            # single line — centred
            c.drawCentredString(cx, page_h - margin - f_title, article)
        else:
            # wrap to 2 lines at last space that fits
            words  = article.split()
            line1  = ""
            for word in words:
                test = (line1 + " " + word).strip()
                if stringWidth(test, "Helvetica-Bold", f_title) <= max_text_w:
                    line1 = test
                else:
                    break
            line2 = article[len(line1):].strip()
            line_gap = f_title + 2
            c.drawCentredString(cx, page_h - margin - f_title,           line1)
            c.drawCentredString(cx, page_h - margin - f_title - line_gap, line2)

        # ── Price — centred vertically and horizontally ─────────────
        c.setFont("Helvetica-Bold", f_price)
        c.drawCentredString(page_w / 2, page_h / 2 - f_price / 2, price_str)

        # ── Pro prices — bottom-right, no € ─────────────────────────
        c.setFont("Helvetica-Bold", f_pro + 1)
        c.setFillColor(colors.black)
        c.drawRightString(page_w - margin, margin, pro_str)

        c.save()
        return output_path
