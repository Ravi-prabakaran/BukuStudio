"""Image handling that needs no image service: cleaning up photos of drawings,
sizing art for print at 300 DPI, turning SVG art into images, and a built-in
sample pencil sketch for tests."""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

DPI = 300


def _paper_light(channel):
    """Estimate how the paper is lit across the photo: remove the thin pencil
    lines with a max filter on a small copy, blur, and scale back up."""
    small = channel.resize((max(1, channel.width // 8), max(1, channel.height // 8)))
    bg = small.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6))
    return bg.resize(channel.size, Image.BILINEAR)


def clean_scan(src, out):
    """'Keep as is': fix rotation, divide out uneven lighting and shadows so the
    paper turns white, darken the pencil, and crop to the drawing with a margin.
    Keeps color if the drawing is colored."""
    import numpy as np
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    channels = []
    for ch in img.split():
        a = np.asarray(ch, dtype=np.float32)
        bg = np.maximum(np.asarray(_paper_light(ch), dtype=np.float32), 1)
        norm = np.clip(a / bg, 0, 1)                       # 1.0 = paper
        norm = np.where(norm > 0.88, 1.0, norm ** 1.6)    # white paper, stronger lines
        channels.append(norm)
    rgb = np.stack(channels, axis=-1)
    colored = float(np.percentile(rgb.max(axis=-1) - rgb.min(axis=-1), 99.5)) > 0.18
    if not colored:
        rgb = np.repeat(rgb.mean(axis=-1, keepdims=True), 3, axis=-1)
    img = Image.fromarray((rgb * 255).astype(np.uint8), "RGB")
    # Table or background showing around the paper touches the photo's edge:
    # flood it white from points along the border.
    step = max(20, min(img.size) // 40)
    seeds = [(x, y) for x in range(0, img.width, step) for y in (0, img.height - 1)] + \
            [(x, y) for y in range(0, img.height, step) for x in (0, img.width - 1)]
    for seed in seeds:
        if sum(img.getpixel(seed)) < 3 * 235:
            ImageDraw.floodfill(img, seed, (255, 255, 255), thresh=70)
    ink = ImageOps.invert(img.convert("L").point(lambda v: 255 if v > 235 else 0)).filter(ImageFilter.MedianFilter(5)).getbbox()
    if ink:
        x0, y0, x1, y1 = ink
        m = int(0.04 * max(img.size))
        img = img.crop((max(0, x0 - m), max(0, y0 - m), min(img.width, x1 + m), min(img.height, y1 + m)))
    img.save(out)
    return out


def fit_for_print(src, out, w_in, h_in, dpi=DPI):
    """Crop to the target shape (keeping the center) and resize to exactly
    w_in x h_in inches at dpi. Returns how much the image was enlarged."""
    img = Image.open(src).convert("RGB")
    tw, th = round(w_in * dpi), round(h_in * dpi)
    scale = max(tw / img.width, th / img.height)
    img = img.resize((max(tw, round(img.width * scale)), max(th, round(img.height * scale))), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    img = img.crop((left, top, left + tw, top + th))
    if scale > 1.2:
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    img.save(out, dpi=(dpi, dpi))
    return round(scale, 2)


def pad_to_aspect(src, out, ratio, fill="white"):
    """Pad an image (no cropping) to width/height = ratio, for sending a drawing
    to an image service without cutting any of it off."""
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if w / h > ratio:
        nw, nh = w, round(w / ratio)
    else:
        nw, nh = round(h * ratio), h
    canvas = Image.new("RGB", (nw, nh), fill)
    canvas.paste(img, ((nw - w) // 2, (nh - h) // 2))
    canvas.save(out)
    return out


def render_svg(svg, out, w_in, h_in, dpi=DPI):
    """Render an SVG picture (with its filters and textures) to exactly w_in x h_in
    inches at dpi, for print."""
    import io
    import resvg_py
    tw, th = round(w_in * dpi), round(h_in * dpi)
    png = resvg_py.svg_to_bytes(svg_string=Path(svg).read_text(), width=tw)
    img = Image.open(io.BytesIO(bytes(png))).convert("RGB")
    tmp = Path(out).with_suffix(".render.png")
    img.save(tmp)
    fit_for_print(tmp, out, w_in, h_in, dpi)
    tmp.unlink()
    return out


def color_under_lines(lines, colors, out):
    """'Light touch' without an image service: Claude's color layer goes under the
    child's own pencil lines (multiply), so every line stays exactly as drawn."""
    line_img = Image.open(lines).convert("RGB")
    color_img = Image.open(colors).convert("RGB").resize(line_img.size, Image.LANCZOS)
    ImageChops.multiply(color_img, line_img).save(out)
    return out


def svg_to_png(svg, out, width_px=1024):
    """Rasterize an SVG (via a one-page PDF) for previews and checks."""
    import pypdfium2 as pdfium
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
    drawing = svg2rlg(str(svg))
    if drawing is None:
        raise ValueError(f"Can't read SVG {svg}")
    tmp = Path(out).with_suffix(".tmp.pdf")
    renderPDF.drawToFile(drawing, str(tmp))
    page = pdfium.PdfDocument(str(tmp))[0]
    page.render(scale=width_px / page.get_width()).to_pil().convert("RGB").save(out)
    tmp.unlink()
    return out


def preview(src, out, side=768):
    img = Image.open(src).convert("RGB")
    img.thumbnail((side, side))
    img.save(out, quality=85)
    return out


def sample_sketch(out, seed=4):
    """A child-style pencil drawing (wobbly fox, sun, flower, house) on slightly
    gray paper with a shadow, like a phone photo, for testing without a real drawing."""
    rnd = random.Random(seed)
    W, H = 1600, 1200
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)

    def wobble(points, width=5, tone=70):
        # Drawn as "ink amount" on black; paper and lighting are applied after.
        pts = [(x + rnd.uniform(-4, 4), y + rnd.uniform(-4, 4)) for x, y in points]
        d.line(pts, fill=255 - tone, width=width, joint="curve")

    def circle(cx, cy, r, n=40):
        return [(cx + r * math.cos(2 * math.pi * i / n) * rnd.uniform(0.95, 1.05),
                 cy + r * math.sin(2 * math.pi * i / n) * rnd.uniform(0.95, 1.05)) for i in range(n + 1)]

    wobble(circle(1300, 230, 110))                       # sun
    for i in range(10):
        a = 2 * math.pi * i / 10
        wobble([(1300 + 135 * math.cos(a), 230 + 135 * math.sin(a)), (1300 + 200 * math.cos(a), 230 + 200 * math.sin(a))], 4)
    wobble([(80, 950), (500, 900), (900, 960), (1520, 920)], 5)   # ground
    wobble(circle(560, 640, 120))                        # fox head
    wobble([(470, 560), (450, 420), (540, 530)])         # ears
    wobble([(650, 560), (670, 420), (580, 530)])
    for ex in (515, 605):
        wobble(circle(ex, 620, 14, 12), 6, 50)
    wobble([(540, 690), (560, 705), (580, 690)], 4)      # smile
    wobble([(500, 760), (470, 900), (650, 900), (620, 760)])  # body
    wobble([(650, 860), (800, 820), (850, 740), (790, 790), (660, 840)])  # tail
    wobble([(1050, 950), (1050, 700), (1300, 700), (1300, 950)])  # house
    wobble([(1020, 710), (1175, 560), (1330, 710)])
    wobble([(1140, 950), (1140, 850), (1210, 850), (1210, 950)], 4)
    wobble([(250, 950), (255, 820)], 4)                  # flower
    wobble(circle(255, 795, 30, 16), 4)
    ink = img.filter(ImageFilter.GaussianBlur(0.8))
    # Paper lit unevenly: bright top-left, a soft hand shadow toward the bottom-right.
    light = Image.radial_gradient("L").resize((W * 2, H * 2)).crop((W // 2 + 300, H // 2 + 250, W // 2 + 300 + W, H // 2 + 250 + H))
    paper = ImageOps.invert(light).point(lambda v: 120 + v * 105 // 255)
    photo = ImageChops.subtract(paper, ink.point(lambda v: v * 3 // 5))
    photo.rotate(1.5, fillcolor=110).convert("RGB").save(out, quality=90)
    return out
