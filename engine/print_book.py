"""Make every file a book needs and check it: interior PDF, cover wrap
(paperback or hardcover), Kindle cover and Kindle eBook (EPUB), KDP preflight
and proof previews.

usage: .venv/bin/python engine/print_book.py books/<book>
prints a JSON summary; exits 1 if preflight found anything KDP would reject.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cover import build_cover  # noqa: E402
from ebook import build_ebook  # noqa: E402
from layout import build_interior  # noqa: E402
from preflight import check  # noqa: E402
from preview import cover_preview, interior_sheet  # noqa: E402


def main(book):
    book = Path(book)
    settings = json.loads((book / "book-settings.json").read_text())
    layout = build_interior(book)
    build_cover(book)   # also makes the Kindle cover, which the eBook includes
    if settings["format"] == "ebook":
        (book / "print" / "cover.pdf").unlink(missing_ok=True)
    ebook = build_ebook(book)
    report = check(book)
    out = book / "print"
    summary = {
        "ok": report["ok"], "pages": layout["pages"], "errors": report["errors"], "warnings": report["warnings"],
        "files": {name: str(out / name) for name in ("interior.pdf", "cover.pdf", "kindle-cover.jpg", "kindle.epub") if (out / name).exists()},
        "ebook": {k: ebook[k] for k in ("layout", "pages", "size_mb")},
        "previews": [str(p) for p in (interior_sheet(book, 40, False), cover_preview(book, 80, False)) if p],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
