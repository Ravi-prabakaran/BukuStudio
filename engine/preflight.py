"""KDP preflight: check a book's print files against Amazon's rules before upload.

usage: .venv/bin/python engine/preflight.py books/<book>
writes print/preflight.json; exits 1 if anything would be rejected.
"""
import json
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kdp  # noqa: E402

TOL = 0.01  # inches


def close(a, b):
    return abs(a - b) <= TOL


def inside(box, area):
    x, y, w, h = box
    ax, ay, aw, ah = area
    return x >= ax - TOL and y >= ay - TOL and x + w <= ax + aw + TOL and y + h <= ay + ah + TOL


def overlaps(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def unembedded_fonts(reader):
    missing = set()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for f in fonts.values():
            f = f.get_object()
            desc = f.get("/FontDescriptor")
            if desc is None and "/DescendantFonts" in f:
                desc = f["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            desc = desc.get_object() if desc is not None else None
            if desc is None or not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                missing.add(str(f.get("/BaseFont")))
    return sorted(missing)


def image_dpi_issues(images, where):
    out = []
    for im in images:
        if im.get("vector"):
            continue
        (pw, ph), (dw, dh) = im["px"], im["drawn_in"]
        dpi = min(pw / dw, ph / dh)
        if dpi < kdp.DPI - 1:
            out.append(f"{where}: {im['file']} prints at {dpi:.0f} DPI; KDP needs {kdp.DPI}.")
    return out


def check(book):
    book = Path(book)
    settings = json.loads((book / "book-settings.json").read_text())
    pr = book / "print"
    errors, warnings, passed = [], [], []

    # Interior
    layout = json.loads((pr / "layout.json").read_text())
    reader = PdfReader(str(pr / "interior.pdf"))
    n = len(reader.pages)
    spec = kdp.Interior(*kdp.trim_size(settings["trim"]), bleed=layout["bleed"], pages=n)
    if n != layout["pages"]:
        errors.append(f"Interior has {n} pages but the layout expected {layout['pages']}.")
    errors += kdp.check_print_options(settings, n)
    sizes = {(round(float(p.mediabox.width) / 72, 3), round(float(p.mediabox.height) / 72, 3)) for p in reader.pages}
    if len(sizes) != 1:
        errors.append(f"Interior pages have different sizes: {sorted(sizes)}.")
    w, h = next(iter(sizes))
    if not (close(w, spec.page_w) and close(h, spec.page_h)):
        errors.append(f"Interior page size is {w} × {h} in; expected {spec.page_w} × {spec.page_h} in "
                      f"({settings['trim']} trim{' plus bleed' if spec.bleed else ''}).")
    else:
        passed.append(f"Interior: {n} pages at {w} × {h} in ({settings['trim']} trim{' plus bleed' if spec.bleed else ''}).")
    missing = unembedded_fonts(reader)
    if missing:
        errors.append(f"Interior fonts not embedded: {', '.join(missing)}.")
    else:
        passed.append("Interior: all fonts embedded.")
    outside = []
    for rec in layout["page_records"]:
        safe = spec.safe_box(rec["page"])
        outside += [rec["page"] for box in rec["texts"] if not inside(box, safe)]
        if rec["overflow"]:
            errors.append(f"Page {rec['page']}: text doesn't fit even at the smallest size. Shorten it.")
        errors += image_dpi_issues(rec["images"], f"Page {rec['page']}")
    if outside:
        errors.append(f"Text outside the safe margins on pages {sorted(set(outside))}.")
    else:
        passed.append(f"Interior: text inside safe margins on every page (gutter {kdp.gutter(n)} in).")
    if layout.get("placeholder_art"):
        missing_art = layout["placeholder_art"]
        warnings.append(f"Placeholder pictures on {len(missing_art)} page(s) ({', '.join(missing_art[:6])}{'…' if len(missing_art) > 6 else ''}). Fine for a test, not for publishing.")
    status = book / "art" / "status.json"
    if status.exists():
        soft = {slot: st["enlarged"] for slot, st in json.loads(status.read_text()).items() if st.get("enlarged", 1) > 2.5}
        if soft:
            worst = max(soft.values())
            warnings.append(f"{len(soft)} picture(s) were enlarged up to {worst}× to reach {kdp.DPI} DPI and may look soft in print "
                            f"({', '.join(sorted(soft)[:6])}{'…' if len(soft) > 6 else ''}). A higher-resolution image model fixes this.")

    # Cover
    cover_pdf = pr / "cover.pdf"
    if settings["format"] == "ebook":
        passed.append("eBook only: no print files needed for upload; interior.pdf is kept as a proof.")
    elif not cover_pdf.exists():
        errors.append("cover.pdf is missing. Run cover.py.")
    else:
        cm = json.loads((pr / "cover.json").read_text())
        cov = kdp.make_cover(settings, n)
        spine = cov.spine
        if settings["format"] == "hardcover":
            warnings.append("Hardcover cover size follows KDP's published wrap and hinge rules; confirm it against "
                            "KDP's cover calculator (kdp.amazon.com/cover-calculator) before uploading.")
        creader = PdfReader(str(cover_pdf))
        cp = creader.pages[0]
        cw, ch = float(cp.mediabox.width) / 72, float(cp.mediabox.height) / 72
        if len(creader.pages) != 1:
            errors.append("Cover PDF must be a single page.")
        if cm["pages"] != n:
            errors.append(f"Cover was made for {cm['pages']} pages but the interior has {n}. Rebuild the cover.")
        if not (close(cw, cov.width) and close(ch, cov.height)):
            errors.append(f"Cover is {cw:.3f} × {ch:.3f} in; expected {cov.width:.3f} × {cov.height:.3f} in "
                          f"(spine {spine:.4f} in for {n} pages).")
        else:
            passed.append(f"Cover: {cw:.3f} × {ch:.3f} in with a {spine:.4f} in spine.")
        if cm["spine_text"] and not cov.spine_text_allowed:
            errors.append(f"Spine text isn't allowed under {kdp.SPINE_TEXT_MIN_PAGES} pages.")
        missing = unembedded_fonts(creader)
        if missing:
            errors.append(f"Cover fonts not embedded: {', '.join(missing)}.")
        else:
            passed.append("Cover: all fonts embedded.")
        for box in cm["texts"]:
            if not (inside(box, cov.safe_front) or inside(box, cov.safe_back)):
                errors.append(f"Cover text at {box} is too close to the edge or spine.")
            if overlaps(box, cov.barcode):
                errors.append("Cover text overlaps the barcode area.")
        if not any(overlaps(b, cov.barcode) for b in cm["texts"]):
            passed.append("Cover: barcode area clear.")
        if any(cm["overflow"].values()):
            errors.append("Cover title or blurb doesn't fit. Shorten it.")
        errors += image_dpi_issues(cm["images"], "Cover")
        if cm.get("placeholder_art"):
            warnings.append("Cover uses placeholder art.")

    kindle = pr / "kindle-cover.jpg"
    if kindle.exists():
        from PIL import Image
        with Image.open(kindle) as im:
            size = im.size
        if size != kdp.KINDLE_COVER_PX:
            errors.append(f"Kindle cover is {size[0]} × {size[1]} px; expected {kdp.KINDLE_COVER_PX[0]} × {kdp.KINDLE_COVER_PX[1]}.")
        else:
            passed.append("Kindle cover: 1600 × 2560 px JPEG.")

    epub = pr / "kindle.epub"
    if epub.exists():
        from ebook import check_epub
        problems = check_epub(epub)
        errors += [f"Kindle eBook: {p}" for p in problems]
        size = epub.stat().st_size / 1e6
        if not problems:
            passed.append(f"Kindle eBook: well-formed EPUB, {size:.1f} MB.")
        if size > 15:
            warnings.append(f"The Kindle eBook is {size:.0f} MB. Amazon charges a delivery fee per MB at the 70% royalty rate; "
                            "large picture books earn less per sale.")
        warnings.append("The eBook passed BukuStudio's structure checks. For the official check, install EPUBCheck "
                        "(brew install epubcheck) and run: epubcheck print/kindle.epub. Also preview it in Kindle Previewer.")

    report = {"ok": not errors, "errors": errors, "warnings": warnings, "passed": passed}
    (pr / "preflight.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = check(sys.argv[1])
    for k, mark in (("passed", "✓"), ("warnings", "!"), ("errors", "✗")):
        for line in r[k]:
            print(f"{mark} {line}")
    sys.exit(0 if r["ok"] else 1)
