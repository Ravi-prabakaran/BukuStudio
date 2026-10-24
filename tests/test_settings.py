import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from settings import fill  # noqa: E402

BASE = {"story": "A little fox finds a lost star.", "author": "Ravi"}


class FillTests(unittest.TestCase):
    def test_defaults_make_a_classic_picture_book_with_no_warnings(self):
        s, warnings, errors = fill(BASE)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(
            {k: s[k] for k in ("audience", "bookType", "format", "trim", "pages", "interior", "paper", "finish", "layout")},
            {"audience": "3-7", "bookType": "picture", "format": "paperback", "trim": "8.5x8.5", "pages": 32,
             "interior": "premium-color", "paper": "white", "finish": "glossy", "layout": "fullbleed-box"},
        )
        self.assertEqual(s["extras"], ["dedication", "the-end"])

    def test_teen_novel_defaults(self):
        s, warnings, _ = fill({**BASE, "audience": "teen"})
        self.assertEqual((s["bookType"], s["trim"], s["pages"], s["interior"], s["paper"], s["finish"]),
                         ("novel", "6x9", "auto", "bw", "cream", "matte"))
        self.assertNotIn("the-end", s["extras"])
        self.assertEqual(warnings, [])

    def test_unavailable_choice_is_replaced(self):
        s, _, _ = fill({**BASE, "bookType": "novel", "trim": "8.5x8.5", "pages": 32})
        self.assertEqual((s["trim"], s["pages"]), ("6x9", "auto"))

    def test_cream_paper_needs_black_and_white(self):
        s, _, _ = fill({**BASE, "paper": "cream"})
        self.assertEqual(s["paper"], "white")

    def test_hardcover_only_for_longer_books_and_kdp_sizes(self):
        s, _, _ = fill({**BASE, "format": "hardcover"})
        self.assertEqual(s["format"], "paperback", "a picture book is too short for a hardcover")
        s, warnings, _ = fill({**BASE, "audience": "teen", "format": "hardcover", "trim": "5x8", "interior": "standard-color"})
        self.assertEqual((s["format"], s["trim"]), ("hardcover", "6x9"))
        self.assertNotEqual(s["interior"], "standard-color")
        self.assertEqual(warnings, [])

    def test_standard_color_short_book_warns(self):
        _, warnings, _ = fill({**BASE, "interior": "standard-color"})
        self.assertTrue(any("72 pages" in w for w in warnings))

    def test_ebook_has_no_cover_finish(self):
        s, _, _ = fill({**BASE, "format": "ebook"})
        self.assertIsNone(s["finish"])

    def test_art_style_follows_the_image_service(self):
        self.assertEqual(fill({**BASE, "imageService": "none"})[0]["artStyle"], "vector")
        self.assertEqual(fill({**BASE, "imageService": "available"})[0]["artStyle"], "watercolor")
        self.assertEqual(fill({**BASE, "imageService": "none", "artStyle": "crayon"})[0]["artStyle"], "crayon")

    def test_story_and_author_required(self):
        _, _, errors = fill({})
        self.assertEqual(errors, ["story is required", "author is required"])


if __name__ == "__main__":
    unittest.main()
