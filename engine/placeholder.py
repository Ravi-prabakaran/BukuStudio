"""Placeholder art drawn as vectors until real pictures exist (Phase 3).
Each scene varies by seed so pages look different, and carries a small label
saying what the real picture will show."""
import random

from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

PALETTES = {
    "color": {"sky": ["#B5D4F4", "#CECBF6", "#FAC775", "#9FE1CB", "#F5C4B3", "#26215C"],
              "hill": ["#97C459", "#5DCAA5", "#639922"], "hill2": ["#3B6D11", "#0F6E56", "#27500A"],
              "sun": "#FAC775", "hero": "#D85A30"},
    "gray": {"sky": ["#E8E8E6", "#D3D1C7", "#F1EFE8"], "hill": ["#B4B2A9", "#A3A19A"], "hill2": ["#888780", "#76756F"],
             "sun": "#C9C8C2", "hero": "#5F5E5A"},
}
INCH = 72


def draw_scene(c, x, y, w, h, seed=0, gray=False, label=None, label_font="Andika"):
    """Draw a simple sky, sun or moon, hills and a small character in the box
    (points). The label, if given, sits in the top-left of the box."""
    rnd = random.Random(seed)
    pal = PALETTES["gray" if gray else "color"]
    sky = rnd.choice(pal["sky"])
    night = sky in ("#26215C",)
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)

    c.setFillColor(HexColor(sky))
    c.rect(x, y, w, h, stroke=0, fill=1)
    if night:
        c.setFillColor(HexColor("#FFFFFF"))
        for _ in range(40):
            c.circle(x + rnd.random() * w, y + h * (0.4 + rnd.random() * 0.6), rnd.uniform(0.6, 1.8), stroke=0, fill=1)

    r = min(w, h) * rnd.uniform(0.07, 0.11)
    c.setFillColor(HexColor(pal["sun"]))
    c.circle(x + w * rnd.uniform(0.6, 0.85), y + h * rnd.uniform(0.68, 0.82), r, stroke=0, fill=1)

    def hill(base, amp, color):
        c.setFillColor(HexColor(color))
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x, y + h * base)
        p.curveTo(x + w * 0.3, y + h * (base + amp), x + w * 0.6, y + h * (base - amp), x + w, y + h * (base + amp * 0.5))
        p.lineTo(x + w, y)
        p.close()
        c.drawPath(p, stroke=0, fill=1)

    hill(rnd.uniform(0.32, 0.42), rnd.uniform(0.06, 0.12), rnd.choice(pal["hill"]))
    hill(rnd.uniform(0.16, 0.22), rnd.uniform(0.03, 0.07), rnd.choice(pal["hill2"]))

    # A small round character with ears, standing on the near hill.
    cx, cy, cr = x + w * rnd.uniform(0.25, 0.45), y + h * 0.3, min(w, h) * 0.06
    c.setFillColor(HexColor(pal["hero"]))
    c.circle(cx, cy, cr, stroke=0, fill=1)
    for side in (-1, 1):
        p = c.beginPath()
        p.moveTo(cx + side * cr * 0.4, cy + cr * 0.75)
        p.lineTo(cx + side * cr * 0.95, cy + cr * 1.6)
        p.lineTo(cx + side * cr * 1.0, cy + cr * 0.3)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(HexColor("#2C2C2A"))
    c.circle(cx - cr * 0.3, cy + cr * 0.15, cr * 0.1, stroke=0, fill=1)
    c.circle(cx + cr * 0.3, cy + cr * 0.15, cr * 0.1, stroke=0, fill=1)
    c.restoreState()

    if label:
        draw_label(c, x, y, w, h, label, label_font)


def draw_label(c, x, y, w, h, text, font):
    style = ParagraphStyle("ph", fontName=font, fontSize=7, leading=8.5, textColor=HexColor("#444441"))
    bw = min(w * 0.6, 3.2 * INCH)
    para = Paragraph(f"<b>Picture coming:</b> {escape(text)}", style)
    _, ph = para.wrap(bw - 12, h)
    pad = 6
    bx, by = x + 0.6 * INCH, y + h - 0.6 * INCH - ph - 2 * pad
    c.saveState()
    c.setFillColor(Color(1, 1, 1, alpha=0.82))
    c.roundRect(bx, by, bw, ph + 2 * pad, 4, stroke=0, fill=1)
    para.drawOn(c, bx + pad, by + pad)
    c.restoreState()


def escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
