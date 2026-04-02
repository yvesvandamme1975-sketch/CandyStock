import io, os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from src.text_cleaner import clean_article

try:
    import barcode as _barcode_mod
    from barcode.writer import ImageWriter as _ImageWriter
    _HAS_BARCODE = True
except ImportError:
    _HAS_BARCODE = False


def _make_barcode_image(ean: str, module_height=15, font_size=10):
    """Generate an EAN barcode PIL Image. Returns None on failure."""
    if not _HAS_BARCODE or not ean:
        return None
    try:
        ean_type = 'ean13' if len(ean) == 13 else 'ean8'
        cls = _barcode_mod.get_barcode_class(ean_type)
        code = cls(ean, writer=_ImageWriter())
        buf = io.BytesIO()
        code.write(buf, options={
            'write_text': True,
            'module_height': module_height,
            'font_size': font_size,
            'quiet_zone': 2,
        })
        buf.seek(0)
        from PIL import Image
        return Image.open(buf).copy()
    except Exception:
        return None

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

        # ── Barcode ── between price and logo, centred ────────────────
        ean = str(product.get("ean", "")).strip()
        barcode_img = _make_barcode_image(ean, module_height=12, font_size=9)
        barcode_bottom = margin + 25 * mm  # reserve space for logo
        if barcode_img:
            bc_buf = io.BytesIO()
            barcode_img.save(bc_buf, format='PNG')
            bc_buf.seek(0)
            bc_reader = ImageReader(bc_buf)
            bw, bh = barcode_img.size
            target_bw = 60 * mm
            bc_scale = target_bw / bw
            draw_bw = target_bw
            draw_bh = bh * bc_scale
            bx = cx - draw_bw / 2
            by = barcode_bottom
            c.drawImage(bc_reader, bx, by, draw_bw, draw_bh, mask='auto')

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

        # Font sizes
        f_title = 11
        f_price = 18

        c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
        c.setFillColor(colors.black)

        max_text_w = page_w - 2 * margin
        cx = page_w / 2
        ean = str(product.get("ean", "")).strip()
        has_barcode = bool(ean) and _HAS_BARCODE

        # ── Layout: top→article, middle→price, bottom→barcode ──────
        # Article at top
        art_y = page_h - margin - f_title
        c.setFont("Helvetica-Bold", f_title)
        if stringWidth(article, "Helvetica-Bold", f_title) <= max_text_w:
            c.drawCentredString(cx, art_y, article)
            art_bottom = art_y - f_title * 0.3
        else:
            words = article.split()
            line1 = ""
            for word in words:
                test = (line1 + " " + word).strip()
                if stringWidth(test, "Helvetica-Bold", f_title) <= max_text_w:
                    line1 = test
                else:
                    break
            line2 = article[len(line1):].strip()
            line_gap = f_title + 1
            c.drawCentredString(cx, art_y, line1)
            c.drawCentredString(cx, art_y - line_gap, line2)
            art_bottom = art_y - line_gap - f_title * 0.3

        # Barcode at bottom (if present)
        barcode_top = margin
        if has_barcode:
            barcode_img = _make_barcode_image(ean, module_height=8, font_size=5)
            if barcode_img:
                bc_buf = io.BytesIO()
                barcode_img.save(bc_buf, format='PNG')
                bc_buf.seek(0)
                bc_reader = ImageReader(bc_buf)
                bw, bh = barcode_img.size
                target_bw = 30 * mm
                bc_scale = target_bw / bw
                draw_bw = target_bw
                draw_bh = bh * bc_scale
                bx = (page_w - draw_bw) / 2
                by = margin * 0.2
                c.drawImage(bc_reader, bx, by, draw_bw, draw_bh, mask='auto')
                barcode_top = by + draw_bh + 1 * mm

        # Price centred between article bottom and barcode top
        price_y = (art_bottom + barcode_top) / 2 - f_price / 2
        c.setFont("Helvetica-Bold", f_price)
        c.drawCentredString(cx, price_y, price_str)

        c.save()
        return output_path
