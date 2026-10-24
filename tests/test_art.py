"""Art pipeline tests, run offline with the fake image service. Needs the
libraries in engine/requirements.txt; skipped without them."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "engine"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401
    import reportlab  # noqa: F401
    import svglib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2588 2625" width="2588" height="2625">
<rect width="2588" height="2625" fill="#B5D4F4"/><circle cx="1900" cy="600" r="250" fill="#FAC775"/>
<rect y="1800" width="2588" height="825" fill="#639922"/></svg>"""


def plan_for(book):
    from layout import art_targets
    slots = {s: {"brief": t["scene"] or "a fox", "characters": ["mia"], "upload": None, "improve": None} for s, t in art_targets(book).items()}
    return {"style": {"summary": "test", "prompt": "watercolor", "palette": [], "avoid": []}, "match_child_style": False,
            "characters": [{"id": "mia", "name": "Mia", "prompt": "a small fox", "reference": None}],
            "slots": slots, "sample_slots": list(slots)[1:3]}


@unittest.skipUnless(HAVE_DEPS, "art dependencies not installed")
class ImagingTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_clean_scan_whitens_shadowed_paper_and_keeps_lines(self):
        import imaging
        from PIL import Image
        src = imaging.sample_sketch(self.dir / "s.jpg")
        out = imaging.clean_scan(src, self.dir / "c.png")
        g = Image.open(out).convert("L")
        hist = g.histogram()
        total = sum(hist)
        self.assertGreater(sum(hist[240:]) / total, 0.9, "paper should be white")
        self.assertGreater(sum(hist[:120]) / total, 0.005, "pencil lines should stay dark")
        with Image.open(src) as raw:
            self.assertLess(sum(raw.convert("L").histogram()[240:]) / total, 0.1, "sample photo starts with gray, shadowed paper")

    def test_fit_for_print_is_exact_size_at_300_dpi(self):
        import imaging
        from PIL import Image
        Image.new("RGB", (1024, 1024), "orange").save(self.dir / "a.png")
        enlarged = imaging.fit_for_print(self.dir / "a.png", self.dir / "b.png", 8.625, 8.75)
        with Image.open(self.dir / "b.png") as im:
            self.assertEqual(im.size, (2588, 2625))
            self.assertEqual(round(im.info["dpi"][0]), 300)
        self.assertAlmostEqual(enlarged, 2.56, places=2)

    def test_pad_to_aspect_never_crops(self):
        import imaging
        from PIL import Image
        Image.new("RGB", (400, 300), "black").save(self.dir / "a.png")
        imaging.pad_to_aspect(self.dir / "a.png", self.dir / "b.png", 1.0)
        with Image.open(self.dir / "b.png") as im:
            self.assertEqual(im.size, (400, 400))
            self.assertEqual(im.getpixel((200, 10)), (255, 255, 255))
            self.assertEqual(im.getpixel((200, 200)), (0, 0, 0))

    def test_svg_to_png(self):
        import imaging
        from PIL import Image
        (self.dir / "a.svg").write_text(SVG)
        imaging.svg_to_png(self.dir / "a.svg", self.dir / "a.png", 400)
        with Image.open(self.dir / "a.png") as im:
            self.assertEqual(im.width, 400)


@unittest.skipUnless(HAVE_DEPS, "art dependencies not installed")
class PipelineTests(unittest.TestCase):
    def make_book(self):
        from test_print import make_book, picture_manuscript
        book = make_book({"artStyle": "watercolor"}, picture_manuscript(32))
        import imaging
        (book / "uploads").mkdir()
        imaging.sample_sketch(book / "uploads" / "page-05.jpg")
        plan = plan_for(book)
        plan["slots"]["page-05"].update({"upload": "uploads/page-05.jpg", "improve": "light"})
        plan["slots"]["page-06"].update({"upload": "uploads/page-05.jpg", "improve": "keep"})
        (book / "art-plan.json").write_text(json.dumps(plan))
        return book

    def test_full_flow_with_fake_service_passes_preflight(self):
        from illustrate import apply_review, disclosure, make_refs, make_slots
        from images import Fake
        from print_book import main as print_main
        book = self.make_book()
        self.assertEqual(list(make_refs(book, Fake())["made"]), ["mia"])
        sample = make_slots(book, Fake(), sample=True)
        self.assertEqual(len(sample["made"]), 2)
        (book / "picture-review.json").write_text(json.dumps({"approved": True, "slots": {s: {"action": "accept"} for s in sample["made"]}}))
        self.assertTrue(apply_review(book)["approved"])
        rest = make_slots(book, Fake())
        status = json.loads((book / "art" / "status.json").read_text())
        self.assertEqual(status["page-05"]["source"], "upload-light")
        self.assertEqual(status["page-06"]["source"], "upload-keep")
        self.assertIsNone(status["page-06"]["provider"])
        self.assertTrue(all(status[s]["approved"] for s in sample["made"]))
        self.assertNotIn("page-06", [s for s in rest["made"] if status[s]["source"] == "generated"])
        self.assertEqual(disclosure(book)["images"], "AI-generated")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(print_main(book), 0)
        layout = json.loads((book / "print" / "layout.json").read_text())
        self.assertEqual(layout["placeholder_art"], [])

    def test_redo_uses_the_note_and_only_remakes_marked_pictures(self):
        from illustrate import apply_review, make_slots
        from images import Fake
        book = self.make_book()
        make_slots(book, Fake())
        prompts = []

        class Spy(Fake):
            def generate(self, prompt, refs=(), aspect="1:1"):
                prompts.append(prompt)
                return super().generate(prompt, refs, aspect)

        (book / "picture-review.json").write_text(json.dumps({"slots": {"page-08": {"action": "redo", "note": "add a red kite"}}}))
        apply_review(book)
        out = make_slots(book, Spy(), redo=True)
        self.assertEqual(out["made"], ["page-08"])
        self.assertIn("add a red kite", prompts[0])
        self.assertEqual(json.loads((book / "art" / "status.json").read_text())["page-08"]["attempts"], 2)
        self.assertEqual(make_slots(book, Spy(), redo=True)["made"], [], "the redo mark is cleared once used")

    def test_original_action_switches_upload_to_keep(self):
        from illustrate import apply_review, make_slots
        from images import Fake
        book = self.make_book()
        make_slots(book, Fake())
        (book / "picture-review.json").write_text(json.dumps({"slots": {"page-05": {"action": "original"}}}))
        self.assertEqual(apply_review(book)["redo_slots"], ["page-05"])
        make_slots(book, Fake(), only={"page-05"})
        self.assertEqual(json.loads((book / "art" / "status.json").read_text())["page-05"]["source"], "upload-keep")

    def draw_jobs(self, book, jobs):
        """Stand in for the vector-artist agent: write a simple SVG for each job."""
        for job in jobs:
            _, _, w, h = job["viewBox"].split()
            body = (f'<rect width="{w}" height="{h}" fill="#F5C4B3" opacity=".8"/>' if job["kind"] == "color-layer" else
                    f'<rect width="{w}" height="{h}" fill="#B5D4F4"/><circle cx="{int(w) // 2}" cy="{int(h) // 2}" r="{int(h) // 5}" fill="#D85A30" filter="url(#kit-watercolor)"/>')
            kit = (ENGINE.parent / "assets" / "svg-kit" / "kit.svg").read_text()
            defs = kit[kit.index("<defs>"):kit.index("</defs>") + 7]
            f = book / job["svg"]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{job["viewBox"]}">{defs}{body}</svg>')

    def test_no_image_service_claude_draws_everything(self):
        from illustrate import disclosure, make_refs, make_slots
        from PIL import Image
        book = self.make_book()
        refs = make_refs(book, None)
        self.assertEqual(refs["made"], {})
        self.assertEqual([j["kind"] for j in refs["for_claude"]], ["character"])
        self.draw_jobs(book, refs["for_claude"])
        self.assertEqual(list(make_refs(book, None)["made"]), ["mia"])

        first = make_slots(book, None, only={"page-04", "page-05", "page-06"})
        kinds = {j["key"]: j["kind"] for j in first["for_claude"]}
        self.assertEqual(kinds, {"page-04": "picture", "page-05": "color-layer"}, "keep needs no drawing")
        self.assertEqual(first["made"], ["page-06"])
        light = next(j for j in first["for_claude"] if j["kind"] == "color-layer")
        self.assertEqual(light["drawing"], "art/raw/page-05-padded.png")
        with Image.open(book / light["drawing"]) as im:
            self.assertEqual(light["viewBox"], f"0 0 {im.width} {im.height}")
        self.assertEqual(len(json.loads((book / "art" / "claude-jobs.json").read_text())), 2)

        self.draw_jobs(book, first["for_claude"])
        second = make_slots(book, None, only={"page-04", "page-05"})
        self.assertEqual(second["made"], ["page-04", "page-05"])
        self.assertEqual(json.loads((book / "art" / "claude-jobs.json").read_text()), [])
        status = json.loads((book / "art" / "status.json").read_text())
        self.assertEqual((status["page-04"]["source"], status["page-04"]["provider"]), ("claude", "claude"))
        self.assertEqual((status["page-05"]["source"], status["page-05"]["provider"]), ("upload-light", "claude"))
        with Image.open(book / "art" / "page-04.png") as im:
            self.assertEqual(im.size, (2588, 2625))
        with Image.open(book / "art" / "page-05.png") as im:
            dark = sum(im.convert("L").histogram()[:100])
            self.assertGreater(dark, 1000, "the child's pencil lines stay on top of Claude's colors")
        self.assertEqual(disclosure(book)["images"], "AI-generated")
        from layout import build_interior
        from preflight import check
        from cover import build_cover
        build_interior(book)
        build_cover(book)
        report = check(book)
        self.assertFalse([e for e in report["errors"] if "font" in e.lower()], "Claude's art must not bring in unembedded fonts")

    def test_claude_redo_archives_the_old_drawing_and_passes_the_note(self):
        from illustrate import apply_review, make_slots
        book = self.make_book()
        self.draw_jobs(book, make_slots(book, None, only={"page-04"})["for_claude"])
        make_slots(book, None, only={"page-04"})
        (book / "picture-review.json").write_text(json.dumps({"slots": {"page-04": {"action": "redo", "note": "add a red kite"}}}))
        apply_review(book)
        job = make_slots(book, None, redo=True)["for_claude"]
        self.assertEqual([(j["key"], j["note"]) for j in job], [("page-04", "add a red kite")])
        self.assertTrue((book / "art" / "raw" / "page-04-v1.svg").exists())
        self.draw_jobs(book, job)
        out = make_slots(book, None, redo=True)
        self.assertEqual(out["made"], ["page-04"])
        self.assertEqual(json.loads((book / "art" / "status.json").read_text())["page-04"]["attempts"], 2)

    def test_simple_shapes_style_uses_claude_even_with_a_service(self):
        from illustrate import make_slots
        from images import Fake
        book = self.make_book()
        settings = json.loads((book / "book-settings.json").read_text())
        settings["artStyle"] = "vector"
        (book / "book-settings.json").write_text(json.dumps(settings))
        out = make_slots(book, Fake(), only={"page-04"})
        self.assertEqual([j["kind"] for j in out["for_claude"]], ["picture"])

    def test_light_touch_with_claude_colors_only_is_ai_assisted(self):
        from illustrate import disclosure
        book = self.make_book()
        (book / "art").mkdir(exist_ok=True)
        (book / "art" / "status.json").write_text(json.dumps({"page-05": {"source": "upload-light"}, "page-06": {"source": "upload-keep"}}))
        self.assertEqual(disclosure(book)["images"], "AI-assisted")


class ServerUploadTests(unittest.TestCase):
    """The page server only accepts images, for known slots, inside the book folder."""

    @classmethod
    def setUpClass(cls):
        import serve
        from http.server import ThreadingHTTPServer
        cls.book = Path(tempfile.mkdtemp())
        serve.Handler.book = cls.book.resolve()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.book, ignore_errors=True)

    def request(self, method, path, data=None):
        req = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_png_upload_and_fetch(self):
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
        code, body = self.request("POST", "/api/upload/page-05", png)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["file"], "uploads/page-05.png")
        self.assertEqual(self.request("GET", "/api/image/uploads/page-05.png")[0], 200)
        self.assertEqual(self.request("DELETE", "/api/upload/page-05")[0], 200)
        self.assertFalse((self.book / "uploads" / "page-05.png").exists())

    def test_rejects_non_images_and_bad_slots(self):
        self.assertEqual(self.request("POST", "/api/upload/page-05", b"<script>")[0], 415)
        self.assertEqual(self.request("POST", "/api/upload/..%2Fevil", b"\xff\xd8\xff" + b"0" * 10)[0], 404)
        self.assertEqual(self.request("POST", "/api/upload/page-5", b"\xff\xd8\xff" + b"0" * 10)[0], 404)

    def test_images_only_from_allowed_folders(self):
        (self.book / "secret.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        self.assertEqual(self.request("GET", "/api/image/secret.png")[0], 404)
        self.assertEqual(self.request("GET", "/api/image/uploads/../secret.png")[0], 404)


if __name__ == "__main__":
    unittest.main()
