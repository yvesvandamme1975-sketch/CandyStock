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

        page_w, page_h = A4[1], A4[0]  # landscape: 297 × 210 mm
        half_w  = page_w / 2  # left A5 zone = 148.5mm
        margin  = 10 * mm
        cx      = half_w / 2  # centre of left half

        c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
        c.setFillColor(colors.black)

        max_w = half_w - 2 * margin

        # ── Article name ── 2cm from top, centred, up to 3 lines ─────
        art_top = page_h - 20 * mm

        def _wrap_lines(text, font_name, font_size, max_width):
            """Wrap text into lines that fit max_width."""
            words = text.split()
            lines = []
            current = ""
            for word in words:
                test = (current + " " + word).strip()
                if stringWidth(test, font_name, font_size) <= max_width:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines

        # Try 1 line at 58pt, then 2 lines at 48pt, then 3 lines shrinking
        art_font = 58
        if stringWidth(article, "Helvetica-Bold", 58) <= max_w:
            # Fits on 1 line
            art_font = 58
            lines = [article]
        else:
            # Try 2 lines at 48pt, shrink if needed
            art_font = 48
            lines = _wrap_lines(article, "Helvetica-Bold", art_font, max_w)
            while len(lines) > 2 and art_font > 36:
                art_font -= 1
                lines = _wrap_lines(article, "Helvetica-Bold", art_font, max_w)
            if len(lines) > 2:
                # Really long — allow 3 lines, shrink to fit
                art_font = 36
                lines = _wrap_lines(article, "Helvetica-Bold", art_font, max_w)
                while len(lines) > 3 and art_font > 20:
                    art_font -= 1
                    lines = _wrap_lines(article, "Helvetica-Bold", art_font, max_w)
        c.setFont("Helvetica-Bold", art_font)
        line_gap = art_font * 1.2
        for j, line in enumerate(lines):
            c.drawCentredString(cx, art_top - j * line_gap, line)

        # ── Price ── middle of page, centred, big ────────────────────
        price_font = 100
        while price_font > 30 and stringWidth(price_str, "Helvetica-Bold", price_font) > max_w:
            price_font -= 2
        c.setFont("Helvetica-Bold", price_font)
        # Place at vertical centre, but ensure gap from article
        price_y = page_h / 2
        art_bottom = art_top - (len(lines) - 1) * line_gap - art_font * 0.3
        min_price_y = art_bottom - price_font - 5 * mm
        if price_y > min_price_y:
            price_y = min_price_y
        c.drawCentredString(cx, price_y, price_str)

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
