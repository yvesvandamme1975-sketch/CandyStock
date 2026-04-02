import io, os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from src.text_cleaner import clean_article

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

        price_str = f"{pvente:.2f}".replace(".", ",") + "\u20ac/HTVA"

        page_w, page_h = A4   # 595.28 × 841.89 pt (210 × 297 mm)
        half_w  = page_w / 2  # left A5 zone = 105mm
        margin  = 10 * mm
        cx      = half_w / 2  # centre of left half

        c = rl_canvas.Canvas(output_path, pagesize=A4)
        c.setFillColor(colors.black)

        max_w = half_w - 2 * margin

        # ── Article name ── 2cm from top, centred ────────────────────
        art_top = page_h - 20 * mm
        art_font = 48
        line1 = article
        line2 = ""
        two_lines = False
        # Try single line first, shrink if needed
        while art_font > 20 and stringWidth(article, "Helvetica-Bold", art_font) > max_w:
            art_font -= 1
        if stringWidth(article, "Helvetica-Bold", art_font) > max_w:
            # Won't fit on one line even at min size — wrap to 2 lines
            art_font = 48
            while art_font > 20:
                words = article.split()
                l1 = ""
                for word in words:
                    test = (l1 + " " + word).strip()
                    if stringWidth(test, "Helvetica-Bold", art_font) <= max_w:
                        l1 = test
                    else:
                        break
                l2 = article[len(l1):].strip()
                if (l1 and
                        stringWidth(l1, "Helvetica-Bold", art_font) <= max_w and
                        stringWidth(l2, "Helvetica-Bold", art_font) <= max_w):
                    break
                art_font -= 1
            line1 = l1
            line2 = l2
            two_lines = True

        c.setFont("Helvetica-Bold", art_font)
        if two_lines:
            c.drawCentredString(cx, art_top, line1)
            c.drawCentredString(cx, art_top - art_font * 1.2, line2)
        else:
            c.drawCentredString(cx, art_top, line1)

        # ── Price ── middle of page, centred, big ────────────────────
        price_font = 80
        while price_font > 30 and stringWidth(price_str, "Helvetica-Bold", price_font) > max_w:
            price_font -= 2
        c.setFont("Helvetica-Bold", price_font)
        c.drawCentredString(cx, page_h / 2, price_str)

        # ── Logo ── bottom, centred ──────────────────────────────────
        if logo_path and os.path.exists(logo_path):
            try:
                logo = ImageReader(logo_path)
                lw, lh = logo.getSize()
                target_w = 80 * mm
                scale = target_w / lw
                draw_w = target_w
                draw_h = lh * scale
                lx = cx - draw_w / 2
                ly = margin
                c.drawImage(logo, lx, ly, draw_w, draw_h, mask='auto')
            except Exception:
                pass

        c.save()
        return output_path

    @staticmethod
    def generate_label(product: dict, output_path: str,
                       logo_path, width_mm: float = 89,
                       height_mm: float = 36) -> str:
        """Generate a label-sized PDF for Dymo LabelWriter 550."""
        article   = clean_article(str(product.get("article", "")).strip())
        pvente    = float(product.get("pvente",    0))

        price_str = f"{pvente:.2f}".replace(".", ",") + "\u20ac/HTVA"

        page_w = width_mm  * mm
        page_h = height_mm * mm
        margin = 3 * mm

        # Golden-ratio font stack (8 → 13 → 21 pt)
        RATIO   = 1.61
        f_title = 13
        f_price = 21

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

        c.save()
        return output_path
