import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
import kdp  # noqa: E402


class KdpTests(unittest.TestCase):
    def test_interior_page_size_adds_bleed_to_one_side_and_top_bottom(self):
        spec = kdp.Interior(8.5, 8.5, bleed=True, pages=32)
        self.assertAlmostEqual(spec.page_w, 8.625)
        self.assertAlmostEqual(spec.page_h, 8.75)
        self.assertEqual(kdp.Interior(6, 9, bleed=False, pages=200).page_w, 6)

    def test_trim_sits_toward_the_spine(self):
        spec = kdp.Interior(8.5, 8.5, bleed=True, pages=32)
        self.assertEqual(spec.trim_box(1)[0], 0)        # right-hand page, bleed on the right
        self.assertEqual(spec.trim_box(2)[0], 0.125)    # left-hand page, bleed on the left

    def test_safe_box_uses_gutter_on_the_spine_side(self):
        spec = kdp.Interior(6, 9, bleed=False, pages=320)
        x1, _, w1, _ = spec.safe_box(1)
        x2, _, w2, _ = spec.safe_box(2)
        self.assertAlmostEqual(x1, 0.625)               # odd page: gutter on the left
        self.assertAlmostEqual(x2, 0.25)                # even page: gutter on the right
        self.assertAlmostEqual(w1, 6 - 0.625 - 0.25)

    def test_gutter_tiers(self):
        self.assertEqual([kdp.gutter(n) for n in (24, 150, 151, 300, 301, 600, 828)], [0.375, 0.375, 0.5, 0.5, 0.625, 0.75, 0.875])

    def test_spine_width(self):
        self.assertAlmostEqual(kdp.spine_width(32, "premium-color", "white"), 0.075104)
        self.assertAlmostEqual(kdp.spine_width(200, "bw", "cream"), 0.5)
        with self.assertRaises(ValueError):
            kdp.spine_width(32, "premium-color", "cream")

    def test_cover_geometry(self):
        cov = kdp.Cover(8.5, 8.5, spine=0.075, pages=32)
        self.assertAlmostEqual(cov.width, 17.325)
        self.assertAlmostEqual(cov.height, 8.75)
        self.assertAlmostEqual(cov.front[0], 8.7)
        self.assertEqual(cov.barcode, (6.375, 0.375, 2.0, 1.2))
        self.assertFalse(cov.spine_text_allowed)
        self.assertFalse(kdp.Cover(6, 9, 0.2, 79).spine_text_allowed)
        self.assertTrue(kdp.Cover(6, 9, 0.2, 80).spine_text_allowed)

    def test_hardcover_cover_geometry(self):
        cov = kdp.make_cover({"trim": "6x9", "format": "hardcover", "interior": "bw", "paper": "cream"}, 100)
        self.assertAlmostEqual(cov.spine, 0.437)
        self.assertAlmostEqual(cov.width, 2 * 0.591 + 2 * 6.197 + 0.437)
        self.assertAlmostEqual(cov.height, 2 * 0.591 + 9.236)
        fx, _, _, _ = cov.front
        sfx, sfy, _, _ = cov.safe_front
        self.assertAlmostEqual(sfx - fx, 0.4, msg="text stays out of the hinge")
        self.assertAlmostEqual(sfy, 0.591 + 0.635)
        bx, by, bw, bh = cov.barcode
        self.assertAlmostEqual(by, 0.591 + 0.76)
        self.assertAlmostEqual(cov.spine_box[0] - (bx + bw), 0.4 + 0.25, msg="barcode clear of the hinge")

    def test_hardcover_rules(self):
        base = {"interior": "bw", "paper": "white", "format": "hardcover", "trim": "6x9"}
        self.assertEqual(kdp.check_print_options(base, 100), [])
        self.assertTrue(any("75 to 550" in e for e in kdp.check_print_options(base, 64)))
        self.assertTrue(any("isn't made in" in e for e in kdp.check_print_options({**base, "trim": "8.5x8.5"}, 100)))
        self.assertTrue(any("can't use" in e for e in kdp.check_print_options({**base, "interior": "standard-color"}, 100)))

    def test_print_option_errors(self):
        base = {"interior": "premium-color", "paper": "white", "format": "paperback", "trim": "8.5x8.5"}
        self.assertEqual(kdp.check_print_options(base, 32), [])
        self.assertTrue(kdp.check_print_options({**base, "interior": "standard-color"}, 32))
        self.assertTrue(kdp.check_print_options(base, 22))
        self.assertTrue(kdp.check_print_options(base, 33))
        self.assertTrue(kdp.check_print_options({**base, "format": "hardcover", "trim": "6x9"}, 32))


if __name__ == "__main__":
    unittest.main()
