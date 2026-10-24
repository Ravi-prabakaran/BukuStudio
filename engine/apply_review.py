"""Apply a checkpoint review to a book: the user's page or chapter edits go into
manuscript.json and the chosen title into listing.json.

usage: python3 engine/apply_review.py books/<book>
prints {"approved", "notes", "edited"}.
"""
import json
import sys
from pathlib import Path


def apply(book):
    book = Path(book)
    review = json.loads((book / "review.json").read_text())
    manuscript_path, listing_path = book / "manuscript.json", book / "listing.json"
    manuscript = json.loads(manuscript_path.read_text())
    listing = json.loads(listing_path.read_text())

    edited = []
    for key, items, edits in (("page", manuscript.get("pages", []), review.get("page_edits", {})),
                              ("number", manuscript.get("chapters", []), review.get("chapter_edits", {}))):
        for item in items:
            new = edits.get(str(item[key]))
            if new is not None and new != item.get("text"):
                item["text"] = new
                edited.append(f"{'page' if key == 'page' else 'chapter'} {item[key]}")
    if edited:
        texts = [p["text"] for p in manuscript.get("pages", []) if p.get("type") == "story"] + \
                [c["text"] for c in manuscript.get("chapters", [])]
        manuscript["word_count"] = sum(len(t.split()) for t in texts)
        manuscript_path.write_text(json.dumps(manuscript, indent=2, ensure_ascii=False) + "\n")

    if review.get("chosen_title"):
        listing["chosen"] = review["chosen_title"]
        listing_path.write_text(json.dumps(listing, indent=2, ensure_ascii=False) + "\n")

    return {"approved": bool(review.get("approved")), "notes": review.get("notes", ""), "edited": edited}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(apply(sys.argv[1]), indent=2, ensure_ascii=False))
