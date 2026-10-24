"""End-to-end print tests: build interiors and covers for sample books and run
preflight. Needs the print dependencies (engine/requirements.txt); skipped without them."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
try:
    import reportlab  # noqa: F401
    import pypdf  # noqa: F401
    import pypdfium2  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False

LISTING = {"title_options": [{"title": "Mia and the Fallen Star", "subtitle": "", "why": ""}], "chosen": None,
           "back_cover_blurb": "A shy fox finds a fallen star and must sing it home."}


def picture_manuscript(pages=32, layout_text_on_odd=True):
    out = [{"page": 1, "type": "title", "text": "", "scene": "Mia"}, {"page": 2, "type": "copyright", "text": "", "scene": ""},
           {"page": 3, "type": "dedication", "text": "For Grandma", "scene": ""}]
    for n in range(4, pages):
        out.append({"page": n, "type": "story", "text": "" if (not layout_text_on_odd and n % 2) else f"Mia walks on page {n}.", "scene": f"scene {n}"})
    out.append({"page": pages, "type": "the-end", "text": "The End", "scene": ""})
    return {"page_count": pages, "word_count": 100, "pages": out}


def make_book(settings, manuscript):
    from settings import fill
    d = Path(tempfile.mkdtemp())
    s, _, errors = fill({"story": "A shy fox finds a star.", "author": "Sam Rivera", **settings})
    assert not errors
    (d / "book-settings.json").write_text(json.dumps(s))
    (d / "manuscript.json").write_text(json.dumps(manuscript))
    (d / "listing.json").write_text(json.dumps(LISTING))
    return d


def build(book):
    from cover import build_cover
    from layout import build_interior
    from preflight import check
    build_interior(book)
    build_cover(book)
    return check(book)


@unittest.skipUnless(HAVE_DEPS, "print dependencies not installed")
class PrintTests(unittest.TestCase):
    def test_picture_book_passes_preflight_in_every_layout(self):
        for layout in ("fullbleed-box", "text-below", "side-by-side"):
            with self.subTest(layout=layout):
                book = make_book({"layout": layout}, picture_manuscript(layout_text_on_odd=layout != "side-by-side"))
                report = build(book)
                self.assertTrue(report["ok"], report["errors"])
                self.assertTrue((book / "print" / "kindle-cover.jpg").exists())

    def test_other_trim_sizes(self):
        for trim, pages in (("8x10", 24), ("8.5x11", 40)):
            with self.subTest(trim=trim):
                report = build(make_book({"trim": trim, "pages": pages}, picture_manuscript(pages)))
                self.assertTrue(report["ok"], report["errors"])

    def test_chapter_book_pads_to_even_and_passes(self):
        chapters = [{"number": i, "title": f"Part {i}", "text": "\n".join(["Mia walked through the woods and listened to the night. " * 12] * 6),
                     "scene": "Mia in the woods"} for i in range(1, 6)]
        book = make_book({"audience": "8-12"}, {"page_count": "auto", "word_count": 5000, "chapters": chapters})
        report = build(book)
        layout = json.loads((book / "print" / "layout.json").read_text())
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(layout["pages"] % 2, 0)
        self.assertGreaterEqual(layout["pages"], 24)
        self.assertFalse(layout["bleed"])

    def chapters(self, n):
        para = "Mia had never seen the woods so quiet, and even the wind seemed to hold its breath. " * 12
        return [{"number": i, "title": f"Night {i}", "text": "\n".join([para] * 5), "scene": "Mia on the path"} for i in range(1, n + 1)]

    def test_hardcover_novel(self):
        book = make_book({"audience": "teen", "format": "hardcover"}, {"page_count": "auto", "word_count": 0, "chapters": self.chapters(40)})
        report = build(book)
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(any("cover-calculator" in w for w in report["warnings"]))
        cover = json.loads((book / "print" / "cover.json").read_text())
        self.assertEqual(cover["format"], "hardcover")
        self.assertIsNotNone(cover["spine_text"])

    def test_short_hardcover_is_rejected(self):
        book = make_book({"audience": "teen", "format": "hardcover"}, {"page_count": "auto", "word_count": 0, "chapters": self.chapters(6)})
        self.assertTrue(any("75 to 550" in e for e in build(book)["errors"]))

    def test_fixed_layout_ebook_for_picture_books(self):
        import zipfile
        from ebook import build_ebook
        book = make_book({}, picture_manuscript(32))
        build(book)
        out = build_ebook(book)
        self.assertEqual((out["layout"], out["pages"], out["problems"]), ("fixed", 32, []))
        with zipfile.ZipFile(book / "print" / "kindle.epub") as z:
            opf = z.read("OEBPS/content.opf").decode()
            self.assertIn("pre-paginated", opf)
            self.assertIn('content="1600x1600"', opf, "8.5x8.5 trim, bleed removed")
            self.assertIn('idref="page-001" properties="page-spread-right"', opf)
            self.assertIn('idref="page-002" properties="page-spread-left"', opf)
            self.assertIn("Mia walks on page 5.", z.read("OEBPS/page-005.xhtml").decode(), "words hidden under the picture")

    def test_reflowable_ebook_for_novels(self):
        import zipfile
        from ebook import build_ebook
        book = make_book({"audience": "teen"}, {"page_count": "auto", "word_count": 0, "chapters": self.chapters(3)})
        build(book)
        out = build_ebook(book)
        self.assertEqual((out["layout"], out["problems"]), ("reflowable", []))
        with zipfile.ZipFile(book / "print" / "kindle.epub") as z:
            self.assertNotIn("pre-paginated", z.read("OEBPS/content.opf").decode())
            self.assertIn("Chapter 2: Night 2", z.read("OEBPS/nav.xhtml").decode())

    def test_ebook_only_has_no_print_cover(self):
        import contextlib
        import io
        from print_book import main
        book = make_book({"format": "ebook"}, picture_manuscript(32))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(book), 0)
        self.assertFalse((book / "print" / "cover.pdf").exists())
        self.assertTrue((book / "print" / "kindle.epub").exists())

    def test_preflight_catches_a_stale_cover(self):
        book = make_book({}, picture_manuscript(32))
        build(book)
        (book / "manuscript.json").write_text(json.dumps(picture_manuscript(40)))
        from layout import build_interior
        from preflight import check
        settings = json.loads((book / "book-settings.json").read_text())
        settings["pages"] = 40
        (book / "book-settings.json").write_text(json.dumps(settings))
        build_interior(book)
        report = check(book)
        self.assertFalse(report["ok"])
        self.assertTrue(any("Rebuild the cover" in e for e in report["errors"]))

    def test_low_resolution_art_is_rejected(self):
        from PIL import Image
        book = make_book({}, picture_manuscript(32))
        (book / "art").mkdir()
        Image.new("RGB", (600, 600), "orange").save(book / "art" / "page-05.png")
        report = build(book)
        self.assertFalse(report["ok"])
        self.assertTrue(any("page-05.png" in e and "DPI" in e for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
