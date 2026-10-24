# BukuStudio

Multi-agent system that turns a story (and optionally a child's drawings) into a publish-ready Amazon KDP book. The full design, inputs, agents and phases are in PLAN.md; read it before starting work and keep it up to date when decisions change. The repo root is the Claude Code plugin (see README.md for the layout).

- Every user choice is a visual picture card, never a typed answer. Include "Recommended", "Not sure? Pick for me", "Good to know" and "Read it to me". New choices go in `wizard/steps.json` with art in `wizard/art.js`.
- `wizard/app.js` and `engine/settings.py` implement the same rules from `wizard/steps.json`; change both together and run `python3 -m unittest discover -s tests`.
- Book file formats are defined in `skills/make-book/reference.md`; agents and scripts must match it.
- Never commit secrets (.env) or anything in books/ (children's drawings, stories, generated books).
- KDP numbers live only in `engine/kdp.py` (bleed, safe margins, gutter tiers, paper thickness, spine text from 80 pages, barcode area, page limits). Don't hard-code them elsewhere.
- Text is placed on pages by code with embedded fonts from `assets/fonts/`, never rendered inside generated images.
- The wizard server, settings and review scripts use only the Python standard library. Print and image code uses `engine/requirements.txt`, installed into `.venv` by `engine/bootstrap.py`; run it with `.venv/bin/python`.
- Image services are optional: everything must work with no key (Claude draws the pictures). Never make a key required.
- Use `BUKU_IMAGE_PROVIDER=fake` (or `--provider fake`) when testing the art pipeline so tests never spend money or need keys. Never read, print or ask for API key values.
- The page server serves only whitelisted book files and images under `uploads/`, `art/preview/`, `art/refs/`; keep it that way and keep `tests/test_art.py` server tests passing.
- After changing print code, run `.venv/bin/python -m unittest discover -s tests` and look at `engine/preview.py --guides` output for a sample book.
