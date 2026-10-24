import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from apply_review import apply  # noqa: E402


def write(d, name, data):
    (d / name).write_text(json.dumps(data))


class ApplyReviewTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        write(self.dir, "manuscript.json", {"word_count": 4, "pages": [
            {"page": 1, "type": "title", "text": ""},
            {"page": 4, "type": "story", "text": "Mia found a star."},
        ]})
        write(self.dir, "listing.json", {"title_options": [{"title": "A"}], "chosen": None})

    def test_edits_and_title_are_applied(self):
        write(self.dir, "review.json", {"approved": True, "chosen_title": {"title": "A", "subtitle": ""},
                                        "page_edits": {"4": "Mia found a tiny, glowing star."}, "notes": ""})
        result = apply(self.dir)
        manuscript = json.loads((self.dir / "manuscript.json").read_text())
        listing = json.loads((self.dir / "listing.json").read_text())
        self.assertEqual(result, {"approved": True, "notes": "", "edited": ["page 4"]})
        self.assertEqual(manuscript["pages"][1]["text"], "Mia found a tiny, glowing star.")
        self.assertEqual(manuscript["word_count"], 6)
        self.assertEqual(listing["chosen"], {"title": "A", "subtitle": ""})

    def test_unchanged_text_is_not_reported(self):
        write(self.dir, "review.json", {"approved": False, "page_edits": {"4": "Mia found a star."}, "notes": "Shorter title"})
        self.assertEqual(apply(self.dir), {"approved": False, "notes": "Shorter title", "edited": []})


if __name__ == "__main__":
    unittest.main()
