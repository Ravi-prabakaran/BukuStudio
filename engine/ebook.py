"""Build the Kindle eBook as an EPUB that KDP accepts.

- Picture books and early readers: fixed-layout EPUB 3. Each page is the printed
  page (trimmed, no bleed) as an image, with the page's words hidden underneath
  for search and accessibility. Pages pair into spreads like the printed book.
- Chapter books and novels: reflowable EPUB 3, so readers can change the text size.

usage: .venv/bin/python engine/ebook.py books/<book>   ->  print/kindle.epub
"""
import datetime
import html
import io
import json
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kdp  # noqa: E402
from layout import load  # noqa: E402

LANG = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Hindi": "hi", "Tamil": "ta", "Telugu": "te",
        "Malayalam": "ml", "Indonesian": "id", "Portuguese": "pt", "Italian": "it", "Japanese": "ja"}
PAGE_LONG_SIDE = 1600   # pixels on the long side of each fixed-layout page
JPEG_QUALITY = 82
esc = html.escape

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""


def xhtml(title, body, lang, head=""):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">
<head><meta charset="UTF-8"/><title>{esc(title)}</title>{head}</head>
<body>{body}</body>
</html>
"""


def nav_doc(title, entries, lang):
    items = "".join(f'<li><a href="{href}">{esc(label)}</a></li>' for label, href in entries)
    return xhtml(title, f'<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{items}</ol></nav>', lang)


def opf(meta, manifest, spine, lang, fixed):
    extra = ""
    if fixed:
        w, h = meta["resolution"]
        extra = f"""
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:spread">landscape</meta>
    <meta name="fixed-layout" content="true"/>
    <meta name="original-resolution" content="{w}x{h}"/>"""
    items = "".join(f'\n    <item id="{i}" href="{href}" media-type="{mt}"{f" properties={chr(34)}{props}{chr(34)}" if props else ""}/>'
                    for i, href, mt, props in manifest)
    refs = "".join(f'\n    <itemref idref="{i}"{f" properties={chr(34)}{props}{chr(34)}" if props else ""}/>' for i, props in spine)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{lang}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:{meta["uuid"]}</dc:identifier>
    <dc:title>{esc(meta["title"])}</dc:title>
    <dc:creator>{esc(meta["author"])}</dc:creator>
    <dc:language>{lang}</dc:language>
    <meta property="dcterms:modified">{datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
    <meta name="cover" content="cover-image"/>{extra}
  </metadata>
  <manifest>{items}
  </manifest>
  <spine>{refs}
  </spine>
</package>
"""


def jpeg(img, max_side=None):
    img = img.convert("RGB")
    if max_side and max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def fixed_layout(book, settings, manuscript, title, lang):
    """One image per printed page, trimmed to the page edge."""
    import pypdfium2 as pdfium
    layout = json.loads((book / "print" / "layout.json").read_text())
    spec = kdp.Interior(*layout["trim_in"], bleed=layout["bleed"], pages=layout["pages"])
    doc = pdfium.PdfDocument(str(book / "print" / "interior.pdf"))
    scale = PAGE_LONG_SIDE / max(spec.trim_w, spec.trim_h) / 72
    w_px, h_px = round(spec.trim_w * 72 * scale), round(spec.trim_h * 72 * scale)
    words = {p["page"]: p.get("text", "") for p in manuscript["pages"]}
    files, manifest, spine, toc = {}, [], [], []
    css = f"html,body{{margin:0;padding:0;width:{w_px}px;height:{h_px}px}}.page{{position:relative;width:{w_px}px;height:{h_px}px;overflow:hidden}}" \
          f".page img{{position:absolute;top:0;left:0;width:{w_px}px;height:{h_px}px}}.words{{position:absolute;left:0;bottom:0;width:100%;opacity:0;font-size:24px}}"
    files["OEBPS/style.css"] = css.encode()
    manifest.append(("css", "style.css", "text/css", None))
    for i, page in enumerate(doc, start=1):
        img = page.render(scale=scale).to_pil()
        x, y, w, h = spec.trim_box(i)
        left, top = round(x * 72 * scale), round((spec.page_h - y - h) * 72 * scale)
        img = img.crop((left, top, left + w_px, top + h_px))
        name = f"page-{i:03d}"
        files[f"OEBPS/images/{name}.jpg"] = jpeg(img)
        text = words.get(i, "")
        body = f'<div class="page"><img src="images/{name}.jpg" alt="{esc(text or f"Page {i}")}"/>' + \
               (f'<div class="words"><p>{esc(text)}</p></div>' if text else "") + "</div>"
        head = f'<meta name="viewport" content="width={w_px}, height={h_px}"/><link rel="stylesheet" href="style.css" type="text/css"/>'
        files[f"OEBPS/{name}.xhtml"] = xhtml(f"{title['title']}, page {i}", body, lang, head).encode()
        manifest += [(f"img-{name}", f"images/{name}.jpg", "image/jpeg", None), (name, f"{name}.xhtml", "application/xhtml+xml", None)]
        spine.append((name, "page-spread-right" if i % 2 else "page-spread-left"))
        if i == 1:
            toc.append((title["title"], f"{name}.xhtml"))
        elif manuscript["pages"][i - 1]["type"] == "story" and len(toc) == 1:
            toc.append(("Story", f"{name}.xhtml"))
    return files, manifest, spine, toc, (w_px, h_px)


def reflowable(book, settings, manuscript, title, lang):
    from PIL import Image
    year = datetime.date.today().year
    css = ("body{font-family:serif;line-height:1.5;margin:0 4%}h1,h2{text-align:center;font-weight:bold}"
           "h2.num{font-size:.9em;font-weight:normal;margin-top:2em;color:#555}p{text-indent:1.5em;margin:0}"
           "p.first{text-indent:0}.center{text-align:center;text-indent:0}.chapter-art{text-align:center;margin:1em 0}"
           ".chapter-art img{max-width:100%}.front{margin-top:30%}")
    files = {"OEBPS/style.css": css.encode()}
    manifest, spine, toc = [("css", "style.css", "text/css", None)], [], []
    head = '<link rel="stylesheet" href="style.css" type="text/css"/>'

    def add(name, label, body, in_toc=True):
        files[f"OEBPS/{name}.xhtml"] = xhtml(label, body, lang, head).encode()
        manifest.append((name, f"{name}.xhtml", "application/xhtml+xml", None))
        spine.append((name, None))
        if in_toc:
            toc.append((label, f"{name}.xhtml"))

    credits = esc(settings["author"]) + (f"<br/>{esc(settings['coauthor'])}" if settings.get("coauthor") else "")
    add("title", title["title"], f'<div class="front"><h1>{esc(title["title"])}</h1>'
        + (f'<p class="center"><i>{esc(title["subtitle"])}</i></p>' if title["subtitle"] else "") + f'<p class="center">{credits}</p></div>')
    add("copyright", "Copyright", f'<p class="center">Text copyright © {year} {esc(settings["author"])}. All rights reserved.</p>', in_toc=False)
    if "dedication" in (settings.get("extras") or []):
        add("dedication", "Dedication", f'<div class="front"><p class="center"><i>{esc(settings.get("dedicationText") or "")}</i></p></div>', in_toc=False)
    for ch in manuscript["chapters"]:
        n = ch["number"]
        art = ""
        for ext in ("png", "jpg"):
            f = book / "art" / f"chapter-{n:02d}.{ext}"
            if f.exists():
                with Image.open(f) as im:
                    files[f"OEBPS/images/chapter-{n:02d}.jpg"] = jpeg(im, 1200)
                manifest.append((f"img-ch{n}", f"images/chapter-{n:02d}.jpg", "image/jpeg", None))
                art = f'<div class="chapter-art"><img src="images/chapter-{n:02d}.jpg" alt="{esc(ch.get("scene", ""))}"/></div>'
                break
        paras = [t.strip() for t in ch["text"].split("\n") if t.strip()]
        body = art + f'<h2 class="num">Chapter {n}</h2><h1>{esc(ch["title"])}</h1>' + \
            "".join(f'<p{" class=\"first\"" if i == 0 else ""}>{esc(t)}</p>' for i, t in enumerate(paras))
        add(f"chapter-{n:02d}", f"Chapter {n}: {ch['title']}", body)
    return files, manifest, spine, toc, None


def build_ebook(book):
    book = Path(book)
    settings, manuscript, title = load(book)
    lang = LANG.get(settings.get("language", "English"), "en")
    fixed = bool(manuscript.get("pages"))
    files, manifest, spine, toc, resolution = (fixed_layout if fixed else reflowable)(book, settings, manuscript, title, lang)

    cover = book / "print" / "kindle-cover.jpg"
    if cover.exists():
        files["OEBPS/images/cover.jpg"] = cover.read_bytes()
        manifest.append(("cover-image", "images/cover.jpg", "image/jpeg", "cover-image"))
    files["OEBPS/nav.xhtml"] = nav_doc(title["title"], toc, lang).encode()
    manifest.append(("nav", "nav.xhtml", "application/xhtml+xml", "nav"))
    meta = {"uuid": uuid.uuid5(uuid.NAMESPACE_URL, f"bukustudio:{book.resolve()}"), "title": title["title"],
            "author": settings["author"], "resolution": resolution}
    files["OEBPS/content.opf"] = opf(meta, manifest, spine, lang, fixed).encode()

    out = book / "print" / "kindle.epub"
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER, compress_type=zipfile.ZIP_DEFLATED)
        for name, data in files.items():
            z.writestr(name, data, compress_type=zipfile.ZIP_STORED if name.endswith(".jpg") else zipfile.ZIP_DEFLATED)
    return {"file": str(out), "layout": "fixed" if fixed else "reflowable", "pages": len(spine),
            "size_mb": round(out.stat().st_size / 1e6, 2), "problems": check_epub(out)}


def check_epub(path):
    """Structural checks: what KDP's converter needs to open the file."""
    import xml.etree.ElementTree as ET
    problems = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        first = z.infolist()[0]
        if first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED or z.read("mimetype") != b"application/epub+zip":
            problems.append("mimetype must be the first, uncompressed file")
        ns = {"opf": "http://www.idpf.org/2007/opf"}
        try:
            root = ET.fromstring(z.read("OEBPS/content.opf"))
        except (KeyError, ET.ParseError) as e:
            return problems + [f"content.opf unreadable: {e}"]
        items = {i.get("id"): i.get("href") for i in root.iterfind("opf:manifest/opf:item", ns)}
        for i, href in items.items():
            if f"OEBPS/{href}" not in names:
                problems.append(f"manifest lists a missing file: {href}")
        for ref in root.iterfind("opf:spine/opf:itemref", ns):
            if ref.get("idref") not in items:
                problems.append(f"spine refers to unknown item {ref.get('idref')}")
        for name in names:
            if name.endswith((".xhtml", ".opf", ".xml")):
                try:
                    ET.fromstring(z.read(name))
                except ET.ParseError as e:
                    problems.append(f"{name} isn't well-formed XML: {e}")
        if not any(i.get("properties") == "nav" for i in root.iterfind("opf:manifest/opf:item", ns)):
            problems.append("no navigation document")
    return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(build_ebook(sys.argv[1]), indent=2))
