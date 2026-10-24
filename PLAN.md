# BukuStudio plan

Turn a story (and, optionally, a child's own drawings) into a publish-ready Amazon KDP book: print-ready interior and cover PDFs, a Kindle eBook, and every listing field KDP asks for.

Built for the author's own family first, then for anyone through Claude.

## Inputs

Only the story and the author name are required. Everything else has a default and is chosen through the visual setup wizard (see below).

| Input | Default | Options |
|---|---|---|
| Core story *(required)* | — | A paragraph up to a full draft |
| Author / pen name *(required)* | — | Printed on the cover |
| Co-author credit | None | "Story by…", "Illustrations by…" |
| Audience / age | Kids 3–7 | 0–3, 3–7, 6–9, 8–12, teen, adult |
| Book type | From age (3–7 → picture book) | Picture book, early reader, chapter book, novel |
| Format | Paperback + Kindle eBook | Hardcover needs 75+ pages |
| Trim size | 8.5×8.5" picture book, 6×9" novel | 8×10", 8.5×11", 5×8", … |
| Page count | 32 for picture books | 24–48 (KDP minimum 24) |
| Interior print | Premium color when illustrated | Standard color, black and white |
| Paper | White | Cream (black-and-white only) |
| Cover finish | Glossy | Matte |
| Art style | Soft watercolor, or matched to uploaded drawings | Cartoon, 3D, crayon, line art, colored pencil, own reference |
| Page layout | Full-bleed picture with text box | Text under picture, text one side / picture the other |
| Characters | Taken from the story | Name, look, clothing, reference drawing or photo |
| Tone | Taken from the story | Funny, cozy, adventurous, sleepy |
| Moral / theme | Taken from the story | Sharing, courage, … |
| Words per page | From age (20–50 for 3–7) | Custom |
| Title | 5 options generated | Own title |
| Language | English | Any |
| Artwork per page | Upload or generate; pages with no upload are generated | — |
| Improve uploaded art? | Ask every time | Keep, Light touch, Full redraw, Vector redraw |
| Upload as character reference | Yes | No |
| Originals gallery page | Yes when anything was uploaded | No |
| Extras | Dedication, "The End" | About the author, discussion questions |
| Mode | Checkpoints on | Fully automatic |

## Visual setup wizard

Every choice is made by tapping large picture cards, never by typing. Each card has a picture, a plain name, a one-line description, and a "Recommended" badge on the default. Every step has "Not sure? Pick for me", a "Good to know" box that explains the current pick for this book (for example, "32 pages is too short for a hardcover"), and a "Read it to me" button.

Layouts, all driven by the same option data and drawings:

- **Cards (main):** grid of picture cards. Approved mockup: `wizard/mockups/format-step.html`.
- **Compare:** a "Compare" link on each step opens a side-by-side table of facts.
- **Kid mode:** a toggle that switches to one big picture at a time with arrows and read-aloud.
- **Chat chips:** for the claude.ai connector, small picture chips inside the conversation.

Steps with pictures: audience, format, trim size (to scale next to a child's hand), page count (thin vs thick), interior print, paper, cover finish, art style (one sample scene in each style), page layout, tone (faces), font (sample sentence), improve-drawing levels (one sketch shown four ways), and a final summary with a 3D mockup of the chosen book.

Option illustrations are vector art drawn in code (`wizard/art.js`). Art-style samples will be generated once and stored in `assets/styles/` (Phase 3); until then the art-style cards use drawn approximations. The wizard never generates images at run time.

Steps, options, recommendations and warnings live in `wizard/steps.json`, shared by the wizard (`wizard/app.js`) and `engine/settings.py`, which fills defaults and validates. A step with only one possible choice is skipped.

Phase 1 runs the wizard as a local web page (`engine/serve.py`) that saves `book-settings.json`; Phase 6 runs it inside Claude as the connector's interactive app.

## Agents

1. **Story Analyst:** characters, setting, arc, theme, age suitability.
2. **Author/Editor:** page-by-page text for the exact page count and reading level, with page-turn moments, dedication and end pages.
3. **Title and Marketing:** titles, subtitle, back-cover blurb, KDP description, 7 keywords, 3 categories, age and grade range.
4. **Art Director:** style guide, character sheet (uploaded drawings become the reference), one illustration brief per page with room for text.
5. **Illustrator:** per page, cleans up and optionally improves the upload, or generates a new image.
6. **Consistency Checker:** Claude reviews every image and sends off-model or unsuitable pages back.
7. **Layout Engine** *(code)*: interior PDF at trim plus bleed, safe margins, embedded fonts, even page count.
8. **Cover Designer** *(code and art)*: back, spine and front wrap; spine width from page count and paper; spine text only at 80+ pages; barcode area clear; Kindle cover 1600×2560.
9. **KDP Preflight QA:** dimensions, DPI, bleed, margins, page count, fonts, spine math, barcode area.

Checkpoints where the user approves: (1) title and page text, (2) character sheet and sample pages, (3) final proof.

## Art per page

- **Upload present:** clean up the scan (straighten, white paper, sharpen, crop, upscale to 300 DPI), then ask:
  - **Keep as is:** clean-up only, no AI.
  - **Light touch:** her lines and composition kept, neatened and colored (sketch-to-image).
  - **Full redraw:** same scene and characters, redrawn in the book's style.
  - **Vector redraw:** Claude redraws it as vector art; free, less faithful.
  Show original and result side by side: Accept, Try again, Use original.
- **No upload:** generate an image matched to the book's style and characters. When some pages were drawn by the child, generated pages match that style.

## Output package

KDP facts this relies on (checked October 2026 against KDP help): hardcover is case laminate in 5.5×8.5, 6×9, 6.14×9.21, 7×10 and 8.25×11, 75 to 550 pages, black ink or premium color (no standard color), 15 mm wrap, 10 mm hinge, text 0.635 in from the book's edge, barcode 2×1.2 in at least 0.76 in from the bottom and 0.25 in from the hinge. The board and spine allowances come from cover calculators matching KDP's; preflight asks users to confirm with KDP's cover calculator. KDP accepts fixed-layout and reflowable EPUB for eBooks; Kindle Kids' Book Creator is reportedly retired.


- `interior.pdf`, `cover.pdf`
- Kindle eBook (fixed-layout EPUB or Kindle Kids' Book Creator input) and `cover.jpg`
- `kdp-listing.md`: every KDP form field, including AI-disclosure answers
- Preview mockups and editable source files

## Tech stack

- Agents: the repo root is the Claude Code plugin: subagents in `agents/`, the `/make-book` coordinator skill and file formats in `skills/make-book/`.
- Wizard and checkpoint review: static web pages (`wizard/`) served by `engine/serve.py`, which exits when the page saves its final answer.
- Print engine (`engine/`): KDP rules in `kdp.py`; `layout.py` (interior PDF), `cover.py` (cover wrap and Kindle cover), `preflight.py`, `preview.py` (proof images), run together by `print_book.py`. Uses ReportLab, pypdf, Pillow and pypdfium2, installed into `.venv` by `bootstrap.py` on first use. Placeholder art (`placeholder.py`) is drawn wherever `art/page-NN.png`, `art/chapter-NN.png` or `art/cover.png` is missing, so Phase 3 only has to drop images in.
- Fonts (`assets/fonts/`, SIL Open Font License): Andika for picture books and early readers (made for beginning readers), Gentium Book Plus for chapter books and novels, Sniglet for titles.
- **Image services are optional.** With no key, Claude draws every picture itself as SVG (the vector-artist agent), in the chosen style, using a tested texture kit (`assets/svg-kit/kit.svg`: watercolor, background wash, crayon, colored pencil, hand-drawn line, 3D shading, paper grain), rendered for print by resvg. "Light touch" without a service is Claude's color layer placed under the child's own pencil lines. The wizard recommends Simple shapes when there's no key and explains each style's Claude version; the art studio's options say who does the work.
- With a key (`OPENAI_API_KEY` or `GEMINI_API_KEY`, optionally `BUKU_IMAGE_PROVIDER`), `engine/images.py` uses OpenAI or Gemini for painted pictures, with character sheets sent along with every picture and the first approved picture as a style anchor. Simple shapes is always drawn by Claude. `fake` is an offline service for tests.
- `illustrate.py` decides per picture: image service, Claude, or the child's drawing kept as is. Claude's drawings go through `art/claude-jobs.json`: run, the agent draws, run again to render.
- Photo clean-up (`engine/imaging.py`): divides out uneven lighting so paper turns white, whitens table edges, crops to the drawing; pictures are cropped and resized to exactly their print size at 300 DPI, and how much each was enlarged is recorded so preflight can warn about soft pictures.
- With an image service, resolution matters as much as quality: a 1024 px image must be enlarged 2.56× to fill an 8.75 in page at 300 DPI. Prefer a model that outputs 2K to 4K. Claude's SVG pictures render at full print resolution.
- Secrets in `.env` (never committed). Children's drawings and generated books in `books/` (never committed).

## Phases

| Phase | Builds | Done when |
|---|---|---|
| 0. Setup ✅ | Repo, structure, this plan | Repo exists on GitHub |
| 1. Wizard and text ✅ | Visual wizard, agents 1–3, checkpoint 1 | A story becomes 32 pages of text plus title and listing |
| 2. Print engine ✅ built | Layout, paperback and hardcover covers, Kindle EPUB (fixed and reflowable), preflight | KDP's previewer accepts the files (still to try) |
| 3. Art ✅ built | Art studio (uploads, improve options), Art Director, Illustrator (`illustrate.py`), Consistency Checker, Vector Artist, picture review (checkpoint 2), no-key mode where Claude draws | A full book mixing drawings and generated pages (tested with Claude's drawings and the offline fake service; a real image service is optional and untried) |
| 4. First real book | Upload to KDP, order a printed proof | The printed book is in hand |
| 5. Plugin release 🔶 packaged | Manifests, install guide (`docs/GETTING-STARTED.md`), privacy note, changelog; needs a public repo and a license decision | Someone else makes a book with it |
| 6. Hosted connector *(optional)* | MCP server with interactive wizard, accounts, payments or own keys, privacy rules | Anyone on claude.ai can use it |

## Rules to keep in mind

- KDP has no upload API: the final upload is manual.
- KDP requires disclosure of AI-generated text and images. Light touch and Full redraw pages count as AI-assisted; Keep as is pages do not.
- Purely AI-generated images may not be protected by US copyright; the author's text and arrangement are.
- KDP limits titles per day and watches for low-effort bulk books; checkpoints protect quality.
- Always order a printed proof before going live.
- Public version: consent for children's uploads, short retention, no training on uploads.

## Open decisions

- Optional image service: only if painted pictures are wanted. Run `.venv/bin/python engine/image_test.py` (built-in sample sketch, or pass a drawing) with OpenAI and/or Gemini keys in `.env`, compare `books/test/compare/comparison.html`, then set `BUKU_IMAGE_PROVIDER`. Judge on keeping the child's drawing, character consistency, and output size.
- Name check before going public: USPTO trademark search, domain, App Store, Amazon. Note that BUKU (buku.io, Dutch textbook platform) exists.

## Phase 6 design: hosted version (not built)

Goal: anyone on claude.ai (web, desktop, phone) makes a book without installing anything.

**How it would work**
- A remote MCP server (a "custom connector" users add in Claude) exposes tools like `start_book`, `save_choices`, `upload_drawing`, `make_pictures`, `build_files`, `get_files`.
- The picture-card wizard, text review, art studio and picture review become MCP Apps (interactive UI shown inside the Claude chat), reusing `wizard/` almost unchanged.
- The engine (`engine/`) runs on the server; finished files come back as download links.
- Claude in the user's chat still does the writing and Claude-drawn pictures, on the user's own Claude plan; the server only stores files, renders and checks them.

**What it needs**
- Hosting: a small container service (for example Fly.io, Render or Google Cloud Run) plus file storage (for example S3 or R2) with automatic deletion.
- Accounts: OAuth sign-in (the MCP authorization flow), one account per family.
- Costs: storage and compute are cents per book. Only optional painted pictures cost real money (roughly $2 to $8 per book); either users bring their own key, or BukuStudio charges per book (Stripe) and uses its own key with a per-account limit.
- Privacy and safety: children's data rules (COPPA in the US, GDPR-K in the EU): the account holder must be a parent, uploads deleted after 30 days or on request, no training on uploads, a public privacy policy, and content checks on uploads.
- Abuse limits: per-account rate limits on picture generation and storage.

**Decisions for the owner**
1. Free with users' own image keys, or paid per book with BukuStudio's key?
2. Which host and region (affects privacy law and cost)?
3. A company or individual as the legal operator (needed for payments and the privacy policy)?

**Rough order:** MCP server with Claude-drawn pictures only (free, no payments) → accounts and storage limits → optional paid painted pictures.
