# BukuStudio

*Your story, made into a real book.*

BukuStudio turns a story, and optionally a child's own drawings, into a publish-ready Amazon KDP book: a print-ready paperback interior and cover, a Kindle eBook, and every listing field KDP asks for. A team of Claude agents writes the pages, plans and checks the art, and lays out the book; every choice is made by tapping picture cards, so kids can use it too.

**Status:** version 0.4.0. Phases 1 to 3 built, plus hardcover covers, the Kindle eBook (EPUB) and install packaging. No API keys needed: Claude draws the pictures itself; an image service is optional for painted pictures. See [PLAN.md](PLAN.md) for the full design.

## Install

In Claude Code:

```
/plugin marketplace add Ravi-prabakaran/BukuStudio
/plugin install bukustudio@bukustudio
```

Then run `/make-book`. See [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) for a step-by-step guide and [PRIVACY.md](PRIVACY.md) for where your family's stories and drawings go.

## How it works today

1. `/make-book` creates `books/<name>/` and opens the visual wizard in your browser.
2. You tap through picture cards (who it's for, format, size, pages, print, paper, cover, art style, layout, feeling, extras). Kid mode shows one big card at a time with read-aloud.
3. The Story Analyst, Author/Editor and Title and Marketing agents write the analysis, the page-by-page text and the KDP listing.
4. A review page opens: pick a title, read every page, fix words in place, or ask for changes.
5. If you have drawings, the art studio page lets you add photos of them for characters, the cover or any page, and choose for each: keep as is, light touch, full redraw, or simple shapes.
6. The Art Director plans every picture. Claude draws them (or an image service paints them, if you've added a key); character sheets and two sample pictures are made first; the Consistency Checker flags off-model pictures; you approve the style, then every picture, on the picture review page (redo any with a note, or use your original).
7. The print engine builds `print/interior.pdf`, `print/cover.pdf` (paperback or hardcover: back, spine, front), `print/kindle-cover.jpg` and `print/kindle.epub`, checks them against KDP's rules, and renders proof images.

## Project layout

The repo root is the Claude Code plugin.

| Path | What |
|---|---|
| `.claude-plugin/` | Plugin and marketplace manifests |
| `agents/` | Story Analyst, Author/Editor, Title and Marketing, Art Director, Consistency Checker, Vector Artist |
| `skills/make-book/` | The `/make-book` coordinator skill and the book file formats (`reference.md`) |
| `wizard/` | Visual wizard (`index.html`), text review (`review.html`), art studio (`studio.html`), picture review (`pictures.html`), card art (`art.js`), steps and rules (`steps.json`) |
| `engine/` | Python: page server, settings, review apply; art (`images.py`, `imaging.py`, `illustrate.py`, `image_test.py`); print engine (`kdp.py`, `layout.py`, `cover.py`, `ebook.py`, `preflight.py`, `preview.py`, `print_book.py`) |
| `tests/` | Unit and end-to-end print tests |
| `assets/fonts/` | Bundled OFL fonts with their licenses |
| `assets/svg-kit/` | Tested SVG textures Claude uses to draw in each style |
| `books/` | Working folders for each book (not committed) |

## Try it

```bash
claude --plugin-dir .                                  # load the plugin from this folder, then run /make-book
python3 engine/serve.py --book books/demo              # or open just the wizard
PY=$(python3 engine/bootstrap.py)                      # one-time: install print libraries into .venv
$PY engine/print_book.py books/demo                    # build and check the print files
$PY -m unittest discover -s tests                      # run all tests
```

Python 3.10+ is required. The wizard needs only the standard library; the print engine's libraries (`engine/requirements.txt`) are installed by `bootstrap.py`. No API key is needed: without one, Claude draws every picture. For painted pictures, optionally add `OPENAI_API_KEY` or `GEMINI_API_KEY` to `.env` (copy `.env.example`) and compare services with `$PY engine/image_test.py`. `BUKU_IMAGE_PROVIDER=fake` runs the pipeline offline with stand-in images.

MIT License, © 2026 Ravi Prabakaran. See [LICENSE](LICENSE). Bundled fonts are under the SIL Open Font License (`assets/fonts/*-OFL.txt`).
