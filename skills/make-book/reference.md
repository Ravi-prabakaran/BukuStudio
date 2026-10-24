# BukuStudio book files

Every book lives in its own folder, `books/<slug>/`, in the user's working directory. Agents read and write these JSON files (UTF-8, 2-space indent). Never put secrets or anything outside the book in them.

## book-settings.json (from the wizard)

```json
{
  "version": 1,
  "story": "Mia the little fox finds a fallen star...",
  "author": "Sam Rivera",
  "coauthor": "",
  "language": "English",
  "audience": "3-7",            // 0-3 | 3-7 | 6-9 | 8-12 | teen | adult
  "bookType": "picture",         // picture | early | chapter | novel
  "format": "paperback",         // paperback | hardcover | ebook (Kindle is always made)
  "trim": "8.5x8.5",
  "pages": 32,                   // number, or "auto" for chapter books and novels
  "interior": "premium-color",   // premium-color | standard-color | bw
  "paper": "white",              // white | cream
  "finish": "glossy",            // glossy | matte | null for eBook only
  "artStyle": "watercolor",
  "layout": "fullbleed-box",     // fullbleed-box | text-below | side-by-side | chapter-art
  "tone": "auto",                // auto | funny | cozy | adventurous | sleepy
  "extras": ["dedication", "the-end"],
  "dedicationText": "",
  "mode": "checkpoints",         // checkpoints | auto
  "drawings": "none",            // none | some
  "imageService": "none"         // available | none (detected, not chosen)
}
```

## story-analysis.json (Story Analyst)

```json
{
  "summary": "Two or three sentences.",
  "characters": [
    {
      "name": "Mia",
      "role": "hero",
      "species": "fox",
      "personality": "shy, kind, brave when it matters",
      "look": "small red fox, white-tipped tail, big amber eyes",
      "clothing": "green scarf",
      "colors": ["#D85A30", "#FFFFFF", "#3B6D11"],
      "from_story": "what the story says, quoted or paraphrased",
      "invented": "details we added and why (empty if none)"
    }
  ],
  "setting": { "places": ["forest at night", "hilltop"], "time": "one night", "world": "gentle woodland" },
  "arc": { "beginning": "", "problem": "", "middle": "", "climax": "", "ending": "" },
  "theme": "courage can be quiet",
  "tone": "cozy",
  "key_moments": ["moments the author clearly cares about, in story order"],
  "favorite_lines": ["exact phrases from the story worth keeping word for word"],
  "age_fit": { "ok": true, "concerns": [], "suggestions": [] },
  "gaps": ["things the story doesn't say that the book will need, with the choice we made"]
}
```

## manuscript.json (Author/Editor)

Picture books and early readers use `pages`; chapter books and novels use `chapters`.

```json
{
  "page_count": 32,
  "word_count": 512,
  "reading_level": "Read-aloud, ages 3-7. Sentences under 15 words.",
  "pages": [
    { "page": 1, "type": "title", "text": "", "scene": "Title page: Mia peeking from behind a tree." },
    { "page": 2, "type": "copyright", "text": "", "scene": "" },
    { "page": 3, "type": "dedication", "text": "For Grandma", "scene": "Small star doodle." },
    { "page": 4, "type": "story", "text": "Deep in the forest...", "scene": "What the picture shows, for the Art Director.", "page_turn": false },
    { "page": 31, "type": "the-end", "text": "The End", "scene": "Mia asleep under a bright star." },
    { "page": 32, "type": "blank", "text": "", "scene": "" }
  ],
  "chapters": [
    { "number": 1, "title": "The Fallen Star", "text": "Full chapter text...", "scene": "Picture at the chapter start." }
  ],
  "changes": ["Plain-language list of what we changed from the author's story and why."]
}
```

Page `type` values: `title`, `copyright`, `dedication`, `story`, `the-end`, `about-author`, `questions`, `blank`.

## listing.json (Title and Marketing)

```json
{
  "title_options": [
    { "title": "Mia and the Fallen Star", "subtitle": "", "why": "Names the hero and the problem." }
  ],
  "chosen": null,
  "back_cover_blurb": "Under 120 words, for the back cover.",
  "description": "KDP description, under 4000 characters. Simple HTML allowed: <p>, <b>, <i>, <br>, <ul>, <li>.",
  "keywords": ["seven entries, each under 50 characters"],
  "categories": ["Juvenile Fiction / Animals / Foxes"],
  "age_range": { "min": 3, "max": 7 },
  "grade_range": { "min": "Preschool", "max": "2" },
  "ai_disclosure": {
    "text": "AI-generated | AI-assisted | none",
    "text_note": "Why, in one sentence.",
    "images": "decided in Phase 3"
  }
}
```

## review.json (checkpoint review page)

```json
{
  "checkpoint": 1,
  "approved": true,
  "chosen_title": { "title": "Mia and the Fallen Star", "subtitle": "" },
  "page_edits": { "4": "New text for page 4" },
  "chapter_edits": { "1": "New text for chapter 1" },
  "notes": "Free-text change requests."
}
```

## print/ (print engine output)

| File | What |
|---|---|
| `interior.pdf` | Every interior page at trim size (plus bleed for picture books and early readers), fonts embedded |
| `cover.pdf` | One page: back, spine and front. Paperback: plus 0.125 in bleed all round. Hardcover: plus the 0.591 in wrap. Not made for eBook only |
| `kindle-cover.jpg` | 1600 × 2560 px Kindle eBook cover |
| `kindle.epub` | Kindle eBook: fixed-layout EPUB 3 for picture books and early readers, reflowable EPUB 3 for chapter books and novels |
| `layout.json`, `cover.json` | What was placed where, for preflight |
| `preflight.json` | `{"ok", "errors", "warnings", "passed"}` from the KDP checks |
| `preview-interior.png`, `preview-cover.png` | Proof images to show the user |

Real pictures go in `art/` as `page-NN.png` (two-digit page number), `chapter-NN.png` and `cover.png`, at least 300 DPI at their printed size. Anything missing is drawn as a placeholder.

## art-choices.json (art studio page)

```json
{
  "uploads": {
    "page-05": { "file": "uploads/page-05.jpg", "improve": "light" },
    "cover": { "file": "uploads/cover.png", "improve": "full" }
  },
  "characters": {
    "mia": { "file": "uploads/character-mia.jpg" }
  }
}
```

`improve` is `keep` (clean-up only), `light` (keep the drawing, neaten and color it), `full` (redraw it in the book's style) or `vector` (Claude redraws it as SVG).

## art-plan.json (Art Director)

```json
{
  "style": {
    "summary": "Soft watercolor with warm night colors.",
    "prompt": "One paragraph used for every picture: medium, lines, palette, light, texture, detail, mood, audience.",
    "palette": ["#D85A30", "#26215C", "#FAC775", "#639922"],
    "avoid": ["photorealism", "scary faces", "busy backgrounds"]
  },
  "match_child_style": false,
  "characters": [
    { "id": "mia", "name": "Mia", "prompt": "Exact, reusable visual description.", "reference": null }
  ],
  "slots": {
    "page-05": { "brief": "What the picture shows.", "characters": ["mia"], "upload": null, "improve": null },
    "cover": { "brief": "...", "characters": ["mia"], "upload": null, "improve": null }
  },
  "sample_slots": ["page-05", "page-20"]
}
```

Slot names: `page-NN` (two-digit page number), `chapter-NN`, `cover`. `PY PLUGIN/engine/illustrate.py targets books/<book>` lists every slot with its size in inches.

## art/ (pictures)

| Path | What |
|---|---|
| `refs/<id>.png`, `refs/<id>.jpg` | Character reference sheets and their previews |
| `<slot>.png` or `<slot>.svg` | Finished picture, sized for print at 300 DPI (SVG is vector) |
| `preview/<slot>.jpg` | Small preview to look at |
| `raw/` | What the image service returned, every attempt |
| `<slot>.svg`, `refs/<id>.svg` | Claude's drawings (vector-artist), rendered to the PNGs above |
| `raw/<slot>-colors.svg` | Claude's color layer for a Light touch drawing without an image service |
| `claude-jobs.json` | Drawings Claude still has to make (see below) |
| `status.json` | Per slot: `source` (`generated`, `claude`, `upload-keep`, `upload-light`, `upload-full`, `upload-vector`), `provider` (`openai`, `gemini`, `fake`, `claude` or null), `model`, `attempts`, `enlarged`, `original`, `approved` |
| `checks.json` | Consistency Checker: per slot `{"ok", "problems", "fix"}` |

## art/claude-jobs.json (drawings for the vector-artist agent)

```json
[
  {
    "key": "page-04",
    "kind": "picture",
    "svg": "art/page-04.svg",
    "viewBox": "0 0 986 1000",
    "w_in": 8.625, "h_in": 8.75,
    "brief": "What the picture shows.",
    "characters": ["mia"],
    "drawing": null,
    "note": "What to change from the last try, or null.",
    "style_reference": "art/page-05.svg",
    "text_space": "Where to keep the picture calm for printed words."
  }
]
```

`kind` is `character` (a reference sheet, written to `art/refs/<id>.svg`), `picture`, or `color-layer` (color only, placed under the child's lines; its `viewBox` is the drawing's pixel size). `drawing` is the child's cleaned-up drawing when there is one.

## picture-review.json (picture review page)

```json
{
  "checkpoint": 2,
  "stage": "sample",
  "approved": false,
  "characters": { "mia": { "action": "accept", "note": "" } },
  "slots": {
    "page-05": { "action": "accept" },
    "page-20": { "action": "redo", "note": "Make Mia smaller and the sky darker" },
    "page-07": { "action": "original" }
  },
  "notes": ""
}
```

`action` is `accept`, `redo` (with a `note`) or, for uploads, `original` (use the clean-up of the author's drawing instead).
