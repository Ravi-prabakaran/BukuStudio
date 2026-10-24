"""Build the print-ready interior PDF for a book, plus a layout manifest that
preflight checks against.

usage: .venv/bin/python engine/layout.py books/<book>
writes books/<book>/print/interior.pdf and print/layout.json
"""
import datetime
import json
import sys
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate, Paragraph, Spacer)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fonts  # noqa: E402
import kdp  # noqa: E402
from placeholder import draw_scene, escape  # noqa: E402

INCH = 72
INK = HexColor("#1F1E1B")
MUTED = HexColor("#5F5E5A")
# Story text size (points) by audience; text shrinks to fit but never below MIN_SIZE.
TEXT_SIZE = {"0-3": 28, "3-7": 20, "6-9": 18, "8-12": 12, "teen": 11.5, "adult": 11.5}
MIN_SIZE = 12


def load(book):
    read = lambda name: json.loads((book / name).read_text())
    settings, manuscript, listing = read("book-settings.json"), read("manuscript.json"), read("listing.json")
    chosen = listing.get("chosen") or listing["title_options"][0]
    return settings, manuscript, {"title": chosen["title"], "subtitle": chosen.get("subtitle", "")}


def credits(settings):
    line = f"by {settings['author']}"
    return line + (f"<br/>{escape(settings['coauthor'])}" if settings.get("coauthor") else "")


def copyright_text(settings):
    year = datetime.date.today().year
    return (f"Text copyright © {year} {escape(settings['author'])}.<br/>"
            f"Illustrations copyright © {year} {escape(settings['author'])}.<br/>All rights reserved.<br/><br/>"
            "No part of this book may be reproduced in any form without written permission "
            "from the author, except for brief quotations in reviews.<br/><br/>First edition.")


def para(text, font, size, align=TA_CENTER, color=INK, leading=1.35):
    style = ParagraphStyle("p", fontName=font, fontSize=size, leading=size * leading, alignment=align, textColor=color)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def fit(text, font, size, w, h, align=TA_CENTER, min_size=MIN_SIZE):
    """Largest paragraph up to `size` that fits w x h points. Returns (para, height, overflow)."""
    s = size
    while True:
        p = para(text, font, s, align)
        _, ph = p.wrap(w, h * 10)
        if ph <= h or s <= min_size:
            return p, ph, ph > h
        s -= 1


# --- art -----------------------------------------------------------------

def art_file(book, slot):
    """The finished picture for a slot like 'page-05', 'chapter-02' or 'cover'.
    Only raster art: Claude's SVGs are rendered to PNG by illustrate.py (with their
    textures), and drawing SVG straight into the PDF would add an unembedded font."""
    for ext in ("png", "jpg", "jpeg"):
        f = book / "art" / f"{slot}.{ext}"
        if f.exists():
            return f
    return None


def art_box(spec, settings, page):
    """Where a picture page's art goes, as (x, y, w, h) in points, or None.
    The illustrator sizes art to exactly this box."""
    no, kind = page["page"], page["type"]
    W, H = spec.page_w * INCH, spec.page_h * INCH
    _, ty, _, th_ = (v * INCH for v in spec.trim_box(no))
    layout = settings["layout"]
    if kind == "title":
        return (0, 0, W, (ty + th_) * 0.55)
    if kind == "the-end":
        return (0, 0, W, (ty + th_) * 0.5)
    if kind == "story":
        if layout == "side-by-side" and no % 2 == 0:
            return None
        if layout == "text-below":
            split = ty + th_ * 0.36
            return (0, split, W, H - split)
        return (0, 0, W, H)
    return None


def draw_art(c, book, page_no, box, record, scene, gray, slot=None):
    """Real art if art/<slot>.png|jpg exists (cropped to fill), else a placeholder."""
    x, y, w, h = box
    f = art_file(book, slot or f"page-{page_no:02d}")
    if f is None:
        draw_scene(c, x, y, w, h, seed=page_no, gray=gray, label=scene or "an illustration")
        return
    from reportlab.lib.utils import ImageReader
    img = ImageReader(str(f))
    iw, ih = img.getSize()
    scale = max(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
    c.restoreState()
    record["images"].append({"file": f.name, "px": [iw, ih], "drawn_in": [round(dw / INCH, 3), round(dh / INCH, 3)]})


# --- picture books and early readers ---------------------------------------

def text_box(c, p, ph, box, record, panel=True, pad=10):
    """Draw paragraph p (height ph) at the bottom of box, on a soft panel."""
    x, y, w, h = box
    if panel:
        c.saveState()
        c.setFillColor(Color(1, 1, 1, alpha=0.9))
        c.roundRect(x - pad, y - pad, w + 2 * pad, ph + 2 * pad, 10, stroke=0, fill=1)
        c.restoreState()
    p.drawOn(c, x, y)
    record["texts"].append([round(v / INCH, 3) for v in (x, y, w, ph)])


def picture_book(book, settings, manuscript, title, out):
    fonts.register()
    pages = manuscript["pages"]
    n = len(pages)
    tw, th = kdp.trim_size(settings["trim"])
    spec = kdp.Interior(tw, th, bleed=True, pages=n)
    font = fonts.body_font(settings)
    size = TEXT_SIZE[settings["audience"]]
    gray = settings["interior"] == "bw"
    layout = settings["layout"]

    c = canvas.Canvas(str(out), pagesize=(spec.page_w * INCH, spec.page_h * INCH), pageCompression=1)
    c.setTitle(title["title"])
    c.setAuthor(settings["author"])
    c.setCreator("BukuStudio")
    records = []

    for pg in pages:
        no, kind, text, scene = pg["page"], pg["type"], pg.get("text", ""), pg.get("scene", "")
        rec = {"page": no, "type": kind, "texts": [], "images": [], "overflow": False}
        sx, sy, sw, sh = (v * INCH for v in spec.safe_box(no))
        tx, ty, tw_, th_ = (v * INCH for v in spec.trim_box(no))

        box = art_box(spec, settings, pg)
        if kind == "title":
            draw_art(c, book, no, box, rec, scene, gray)
            block = f"{title['title']}" + (f"\n{title['subtitle']}" if title["subtitle"] else "")
            p, ph, over = fit(block, "Sniglet-ExtraBold", 40, sw, sh * 0.28, min_size=18)
            p.drawOn(c, sx, sy + sh - ph)
            rec["texts"].append([round(v / INCH, 3) for v in (sx, sy + sh - ph, sw, ph)])
            a = Paragraph(credits(settings), ParagraphStyle("a", fontName=font, fontSize=16, leading=21, alignment=TA_CENTER, textColor=MUTED))
            _, ah = a.wrap(sw, sh)
            a.drawOn(c, sx, sy + sh - ph - 14 - ah)
            rec["texts"].append([round(v / INCH, 3) for v in (sx, sy + sh - ph - 14 - ah, sw, ah)])
            rec["overflow"] = over
        elif kind == "copyright":
            p = Paragraph(copyright_text(settings), ParagraphStyle("c", fontName=font, fontSize=9, leading=13, textColor=MUTED))
            _, ph = p.wrap(sw, sh)
            p.drawOn(c, sx, sy)
            rec["texts"].append([round(v / INCH, 3) for v in (sx, sy, sw, ph)])
        elif kind == "dedication":
            p, ph, over = fit(text, font, 18, sw * 0.8, sh * 0.4)
            p.drawOn(c, sx + sw * 0.1, sy + sh * 0.6 - ph / 2)
            rec["texts"].append([round(v / INCH, 3) for v in (sx + sw * 0.1, sy + sh * 0.6 - ph / 2, sw * 0.8, ph)])
            rec["overflow"] = over
        elif kind == "story":
            if layout == "side-by-side" and no % 2 == 0:
                p, ph, over = fit(text, font, size + 4, sw, sh)
                p.drawOn(c, sx, sy + (sh - ph) / 2)
                rec["texts"].append([round(v / INCH, 3) for v in (sx, sy + (sh - ph) / 2, sw, ph)])
            elif layout == "text-below":
                split = box[1]
                draw_art(c, book, no, box, rec, scene, gray)
                p, ph, over = fit(text, font, size, sw, split - sy - 12)
                text_box(c, p, ph, (sx, sy + (split - sy - 12 - ph) / 2, sw, ph), rec, panel=False)
            else:
                draw_art(c, book, no, box, rec, scene, gray)
                if text:
                    p, ph, over = fit(text, font, size, sw - 20, sh * 0.38)
                    text_box(c, p, ph, (sx + 10, sy + 10, sw - 20, ph), rec)
                else:
                    over = False
            rec["overflow"] = over
        elif kind == "the-end":
            draw_art(c, book, no, box, rec, scene, gray)
            p, ph, _ = fit(text or "The End", "Sniglet-ExtraBold", 44, sw, sh * 0.3)
            p.drawOn(c, sx, sy + sh * 0.72 - ph / 2)
            rec["texts"].append([round(v / INCH, 3) for v in (sx, sy + sh * 0.72 - ph / 2, sw, ph)])
        elif kind in ("about-author", "questions"):
            heading = "About the Author" if kind == "about-author" else "Let's Talk About the Story"
            h = para(heading, "Sniglet-ExtraBold", 24)
            _, hh = h.wrap(sw, sh)
            h.drawOn(c, sx, sy + sh - hh)
            p, ph, over = fit(text, font, 16, sw, sh - hh - 24, align=TA_LEFT)
            p.drawOn(c, sx, sy + sh - hh - 24 - ph)
            rec["texts"] += [[round(v / INCH, 3) for v in b] for b in ((sx, sy + sh - hh, sw, hh), (sx, sy + sh - hh - 24 - ph, sw, ph))]
            rec["overflow"] = over
        records.append(rec)
        c.showPage()
    c.save()
    return spec, records


# --- chapter books and novels ------------------------------------------------

class ChapterArt(Flowable):
    """Picture at the top of a chapter (real file if present, else placeholder)."""

    def __init__(self, book, number, scene, width, gray):
        super().__init__()
        self.book, self.number, self.scene, self.w, self.gray = book, number, scene, width, gray
        self.h = width * 0.55

    def wrap(self, aw, ah):
        return self.w, self.h + 18

    def draw(self):
        draw_art(self.canv, self.book, 100 + self.number, (0, 18, self.w, self.h), {"images": []}, self.scene, self.gray,
                 slot=f"chapter-{self.number:02d}")


def chapter_book(book, settings, manuscript, title, out):
    fonts.register()
    tw, th = kdp.trim_size(settings["trim"])
    size = TEXT_SIZE[settings["audience"]]
    gray = settings["interior"] == "bw"
    body = ParagraphStyle("body", fontName="Gentium", fontSize=size, leading=size * 1.45, firstLineIndent=size * 1.5, textColor=INK)
    first = ParagraphStyle("first", parent=body, firstLineIndent=0)
    center = lambda s, f="Gentium", c=INK: ParagraphStyle("c", fontName=f, fontSize=s, leading=s * 1.3, alignment=TA_CENTER, textColor=c)

    def build(estimate, blanks=0):
        spec = kdp.Interior(tw, th, bleed=False, pages=estimate)
        templates = []
        for tid, page_no, nxt in (("right", 1, "left"), ("left", 2, "right")):
            x, y, w, h = (v * INCH for v in spec.safe_box(page_no))
            templates.append(PageTemplate(id=tid, frames=[Frame(x, y + 18, w, h - 18, 0, 0, 0, 0, id=tid)],
                                          autoNextPageTemplate=nxt, onPage=page_number))
        doc = BaseDocTemplate(str(out), pagesize=(spec.page_w * INCH, spec.page_h * INCH), pageTemplates=templates,
                              title=title["title"], author=settings["author"], creator="BukuStudio")
        frame_w = templates[0].frames[0]._width
        story = [Spacer(1, 1.6 * INCH), Paragraph(escape(title["title"]), center(30, "Gentium-Bold"))]
        if title["subtitle"]:
            story += [Spacer(1, 8), Paragraph(escape(title["subtitle"]), center(16, "Gentium-Italic"))]
        story += [Spacer(1, 30), Paragraph(credits(settings), center(14, c=MUTED)), PageBreak(),
                  Spacer(1, (th - 3.2) * INCH), Paragraph(copyright_text(settings), ParagraphStyle("cr", fontName="Gentium", fontSize=9, leading=13, textColor=MUTED)), PageBreak()]
        if "dedication" in (settings.get("extras") or []):
            story += [Spacer(1, 2 * INCH), Paragraph(escape(settings.get("dedicationText") or "For ___"), center(14, "Gentium-Italic")), PageBreak()]
        for ch in manuscript["chapters"]:
            story.append(ChapterArt(book, ch["number"], ch.get("scene", ""), frame_w, gray))
            story += [Paragraph(f"Chapter {ch['number']}", center(12, c=MUTED)), Spacer(1, 4),
                      Paragraph(escape(ch["title"]), center(20, "Gentium-Bold")), Spacer(1, 16)]
            paras = [t.strip() for t in ch["text"].split("\n") if t.strip()]
            story += [Paragraph(escape(t), first if i == 0 else body) for i, t in enumerate(paras)]
            story.append(PageBreak())
        for _ in range(blanks):
            story += [Spacer(1, 1), PageBreak()]
        doc.build(story)
        return spec, doc.page

    def page_number(c, doc):
        if doc.page > 3:
            spec = kdp.Interior(tw, th, bleed=False, pages=max(doc.page, 24))
            x, y, w, _ = (v * INCH for v in spec.safe_box(doc.page))
            c.setFont("Gentium", 9)
            c.setFillColor(MUTED)
            (c.drawRightString if doc.page % 2 else c.drawString)(x + w if doc.page % 2 else x, y, str(doc.page))

    spec, n = build(100)
    if kdp.gutter(n) != kdp.gutter(100):
        spec, n = build(n)
    target = max(n + (n % 2), 24)
    if target != n:
        spec, n = build(n, blanks=target - n)
    spec.pages = n
    # Text flows inside each page's frame: the safe box, less room at the bottom for the page number.
    frame = lambda i: [round(v, 3) for v in (lambda x, y, w, h: (x, y + 18 / INCH, w, h - 18 / INCH))(*spec.safe_box(i))]
    return spec, [{"page": i, "type": "flow", "texts": [frame(i)], "images": [], "overflow": False} for i in range(1, n + 1)]


def chapter_art_size(settings):
    """Chapter-start picture size in inches: the text width, 0.55 as tall."""
    tw, th = kdp.trim_size(settings["trim"])
    w = kdp.Interior(tw, th, bleed=False, pages=100).safe_box(1)[2]
    return w, w * 0.55


def art_targets(book):
    """Every picture the book needs: {slot: {"w_in", "h_in", "scene"}}."""
    settings, manuscript, _ = load(Path(book))
    tw, th = kdp.trim_size(settings["trim"])
    targets = {}
    if manuscript.get("pages"):
        spec = kdp.Interior(tw, th, bleed=True, pages=len(manuscript["pages"]))
        for pg in manuscript["pages"]:
            box = art_box(spec, settings, pg)
            if box:
                targets[f"page-{pg['page']:02d}"] = {"w_in": box[2] / INCH, "h_in": box[3] / INCH, "scene": pg.get("scene", "")}
    else:
        w, h = chapter_art_size(settings)
        for ch in manuscript["chapters"]:
            targets[f"chapter-{ch['number']:02d}"] = {"w_in": w, "h_in": h, "scene": ch.get("scene", "")}
    if settings["format"] != "ebook":
        targets["cover"] = {"w_in": tw + kdp.BLEED, "h_in": th + 2 * kdp.BLEED, "scene": "front cover"}
    else:
        targets["cover"] = {"w_in": 6.25, "h_in": 10.0, "scene": "front cover"}
    return targets


def build_interior(book):
    book = Path(book)
    settings, manuscript, title = load(book)
    out_dir = book / "print"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "interior.pdf"
    if manuscript.get("pages"):
        spec, records = picture_book(book, settings, manuscript, title, out)
        kind = "picture"
    else:
        spec, records = chapter_book(book, settings, manuscript, title, out)
        kind = "chapter"
    manifest = {
        "kind": kind, "title": title, "pages": spec.pages, "bleed": spec.bleed,
        "trim_in": [spec.trim_w, spec.trim_h], "page_in": [round(spec.page_w, 4), round(spec.page_h, 4)],
        "gutter_in": kdp.gutter(spec.pages), "placeholder_art": [slot for slot in art_targets(book) if slot != "cover" and not art_file(book, slot)], "page_records": records,
    }
    (out_dir / "layout.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    m = build_interior(sys.argv[1])
    print(json.dumps({k: m[k] for k in ("kind", "pages", "page_in", "gutter_in", "placeholder_art")}))
