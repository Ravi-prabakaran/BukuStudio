"""Render proof images of a book's print files: a contact sheet of interior
spreads and the cover, with optional trim (red) and safe-zone (blue) guides.

usage: .venv/bin/python engine/preview.py books/<book> [--guides] [--dpi 40]
writes books/<book>/print/preview-interior.png and preview-cover.png
"""
import argparse
import json
import sys
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kdp  # noqa: E402


def render(pdf, dpi):
    doc = pdfium.PdfDocument(str(pdf))
    return [page.render(scale=dpi / 72).to_pil().convert("RGB") for page in doc]


def guide(img, box_in, page_h_in, dpi, color, width=1):
    x, y, w, h = box_in
    d = ImageDraw.Draw(img)
    top = (page_h_in - y - h) * dpi
    d.rectangle([x * dpi, top, (x + w) * dpi, top + h * dpi], outline=color, width=width)


def interior_sheet(book, dpi, guides):
    pdf = book / "print" / "interior.pdf"
    m = json.loads((book / "print" / "layout.json").read_text())
    pages = render(pdf, dpi)
    spec = kdp.Interior(*m["trim_in"], bleed=m["bleed"], pages=m["pages"])
    if guides:
        for i, img in enumerate(pages, start=1):
            guide(img, spec.trim_box(i), spec.page_h, dpi, (226, 75, 74))
            guide(img, spec.safe_box(i), spec.page_h, dpi, (55, 138, 221))
    pw, ph = pages[0].size
    # Page 1 sits alone on the right, then spreads (2-3, 4-5, ...), like a printed book.
    spreads = [[None, pages[0]]] + [pages[i:i + 2] for i in range(1, len(pages), 2)]
    cols, gap = 4, 16
    rows = (len(spreads) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (2 * pw + gap) + gap, rows * (ph + gap) + gap), (241, 239, 232))
    for i, spread in enumerate(spreads):
        ox, oy = gap + (i % cols) * (2 * pw + gap), gap + (i // cols) * (ph + gap)
        for j, img in enumerate(spread):
            if img is not None:
                sheet.paste(img, (ox + j * pw, oy))
    out = book / "print" / "preview-interior.png"
    sheet.save(out)
    return out


def cover_preview(book, dpi, guides):
    pdf = book / "print" / "cover.pdf"
    if not pdf.exists():
        return None
    img = render(pdf, dpi)[0]
    if guides:
        m = json.loads((book / "print" / "cover.json").read_text())
        kind = kdp.HardcoverCover if m.get("format") == "hardcover" else kdp.Cover
        cov = kind(*m["trim_in"], spine=m["spine_in"], pages=m["pages"])
        for box, color in ((cov.back, (226, 75, 74)), (cov.front, (226, 75, 74)), (cov.spine_box, (226, 75, 74)),
                           (cov.safe_front, (55, 138, 221)), (cov.safe_back, (55, 138, 221)), (cov.barcode, (186, 117, 23))):
            guide(img, box, cov.height, dpi, color)
    out = book / "print" / "preview-cover.png"
    img.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--guides", action="store_true")
    ap.add_argument("--dpi", type=int, default=40)
    a = ap.parse_args()
    book = Path(a.book)
    print(json.dumps({"interior": str(interior_sheet(book, a.dpi, a.guides)), "cover": str(cover_preview(book, a.dpi * 2, a.guides))}))
