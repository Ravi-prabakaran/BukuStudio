"""Build the paperback cover wrap (back, spine, front) and the Kindle cover.

usage: .venv/bin/python engine/cover.py books/<book>
needs print/layout.json from layout.py (for the final page count).
writes print/cover.pdf, print/cover.json and print/kindle-cover.jpg
"""
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fonts  # noqa: E402
import kdp  # noqa: E402
from layout import art_file, fit, load  # noqa: E402
from placeholder import draw_scene, escape  # noqa: E402

INCH = 72
COVER_BG = "#3C3489"
SPINE_BG = "#26215C"


def draw_front(c, book, settings, title, box, record, gray):
    """Front cover inside box (points, including any bleed you pass in)."""
    x, y, w, h = box
    art = art_file(book, "cover")
    if art:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(str(art))
        iw, ih = img.getSize()
        s = max(w / iw, h / ih)
        c.saveState()
        p = c.beginPath()
        p.rect(x, y, w, h)
        c.clipPath(p, stroke=0, fill=0)
        c.drawImage(img, x + (w - iw * s) / 2, y + (h - ih * s) / 2, iw * s, ih * s)
        c.restoreState()
        record["images"].append({"file": art.name, "px": [iw, ih], "drawn_in": [round(iw * s / INCH, 3), round(ih * s / INCH, 3)]})
    else:
        draw_scene(c, x, y, w, h, seed=7, gray=gray)
    return art is not None


def front_text(c, settings, title, safe, record):
    sx, sy, sw, sh = safe
    block = title["title"] + (f"\n{title['subtitle']}" if title["subtitle"] else "")
    p, ph, over = fit(block, "Sniglet-ExtraBold", 54, sw - 24, sh * 0.32, min_size=20)
    panel(c, sx, sy + sh - ph - 24, sw, ph + 24)
    p.drawOn(c, sx + 12, sy + sh - ph - 12)
    a = Paragraph(escape(settings["author"]) + (f"<br/><font size=13>{escape(settings['coauthor'])}</font>" if settings.get("coauthor") else ""),
                  ParagraphStyle("a", fontName="Andika-Bold", fontSize=20, leading=24, alignment=TA_CENTER, textColor=HexColor("#1F1E1B")))
    _, ah = a.wrap(sw - 24, sh)
    panel(c, sx + sw * 0.15, sy, sw * 0.7, ah + 16)
    a.drawOn(c, sx + 12, sy + 8)
    record["texts"] += [[round(v / INCH, 3) for v in b] for b in ((sx, sy + sh - ph - 24, sw, ph + 24), (sx + sw * 0.15, sy, sw * 0.7, ah + 16))]
    return over


def panel(c, x, y, w, h):
    c.saveState()
    c.setFillColor(Color(1, 1, 1, alpha=0.88))
    c.roundRect(x, y, w, h, 12, stroke=0, fill=1)
    c.restoreState()


def build_cover(book):
    book = Path(book)
    fonts.register()
    settings, _, title = load(book)
    listing = json.loads((book / "listing.json").read_text())
    layout = json.loads((book / "print" / "layout.json").read_text())
    pages = layout["pages"]
    tw, th = kdp.trim_size(settings["trim"])
    cov = kdp.make_cover(settings, pages)
    spine = cov.spine
    inset = lambda box, d: (box[0] + d, box[1] + d, box[2] - 2 * d, box[3] - 2 * d)
    gray = False  # covers always print in color, whatever the interior ink
    out = book / "print" / "cover.pdf"
    rec = {"texts": [], "images": []}

    c = canvas.Canvas(str(out), pagesize=(cov.width * INCH, cov.height * INCH), pageCompression=1)
    c.setTitle(f"{title['title']} cover")
    c.setAuthor(settings["author"])
    c.setCreator("BukuStudio")
    W, H = cov.width * INCH, cov.height * INCH

    # Back and spine background, running into the bleed (and the hardcover wrap).
    c.setFillColor(HexColor(COVER_BG))
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # Front: art bleeds off the top, bottom and right edges.
    fx = cov.front[0] * INCH
    has_art = draw_front(c, book, settings, title, (fx, 0, W - fx, H), rec, gray)
    title_over = front_text(c, settings, title, tuple(v * INCH for v in inset(cov.safe_front, 0.25)), rec)

    # Spine.
    sx, sy, sw, sh = (v * INCH for v in cov.spine_box)
    c.setFillColor(HexColor(SPINE_BG))
    c.rect(sx, 0, sw, H, stroke=0, fill=1)
    spine_text = None
    if cov.spine_text_allowed:
        size = min(14, (sw - 2 * kdp.SPINE_TEXT_MARGIN * INCH) * 0.7)
        spine_text = f"{title['title']}  ·  {settings['author']}"
        c.saveState()
        c.translate(sx + sw / 2 + size * 0.35, sy + sh / 2)
        c.rotate(-90)
        c.setFont("Sniglet-ExtraBold", size)
        c.setFillColor(HexColor("#FFFFFF"))
        c.drawCentredString(0, 0, spine_text)
        c.restoreState()

    # Back: blurb on a panel, barcode area left clear (KDP prints the barcode there).
    sbx, sby, sbw, sbh = inset(cov.safe_back, 0.25)
    above_barcode = cov.barcode[1] + cov.barcode[3] + 0.3
    blurb_box = tuple(v * INCH for v in (sbx, above_barcode, sbw, sby + sbh - above_barcode))
    p, ph, blurb_over = fit(listing.get("back_cover_blurb", ""), "Andika", 15, blurb_box[2] - 32, blurb_box[3] - 32, align=TA_LEFT, min_size=10)
    panel(c, blurb_box[0], blurb_box[1] + blurb_box[3] - ph - 32, blurb_box[2], ph + 32)
    p.drawOn(c, blurb_box[0] + 16, blurb_box[1] + blurb_box[3] - ph - 16)
    rec["texts"].append([round(v / INCH, 3) for v in (blurb_box[0], blurb_box[1] + blurb_box[3] - ph - 32, blurb_box[2], ph + 32)])
    gx, gy, gw, gh = (v * INCH for v in cov.barcode)
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(gx, gy, gw, gh, stroke=0, fill=1)
    c.showPage()
    c.save()

    manifest = {
        "format": settings["format"], "pages": pages, "trim_in": [tw, th], "spine_in": round(spine, 4),
        "size_in": [round(cov.width, 4), round(cov.height, 4)], "spine_text": spine_text,
        "barcode_in": [round(v, 4) for v in cov.barcode], "placeholder_art": not has_art,
        "overflow": {"title": title_over, "blurb": blurb_over}, **rec,
    }
    (book / "print" / "cover.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    kindle_cover(book, settings, title, gray)
    return manifest


def kindle_cover(book, settings, title, gray):
    """Kindle eBook cover: 1600 x 2560 px JPEG, the front design at a 1:1.6 ratio."""
    w_px, h_px = kdp.KINDLE_COVER_PX
    w, h = 6.25 * INCH, 10 * INCH
    tmp = book / "print" / ".kindle-cover.pdf"
    c = canvas.Canvas(str(tmp), pagesize=(w, h))
    draw_front(c, book, settings, title, (0, 0, w, h), {"images": []}, gray)
    m = 0.4 * INCH
    front_text(c, settings, title, (m, m, w - 2 * m, h - 2 * m), {"texts": []})
    c.showPage()
    c.save()
    page = pdfium.PdfDocument(str(tmp))[0]
    img = page.render(scale=w_px / w).to_pil().convert("RGB").resize((w_px, h_px))
    img.save(book / "print" / "kindle-cover.jpg", quality=92)
    tmp.unlink()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    m = build_cover(sys.argv[1])
    print(json.dumps({k: m[k] for k in ("pages", "size_in", "spine_in", "spine_text", "placeholder_art", "overflow")}))
