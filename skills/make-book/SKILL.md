---
name: make-book
description: Make a publish-ready Amazon KDP book with BukuStudio from a story, through a visual picture-card wizard and a team of agents. Use when the user wants to make, write, or publish a book (picture book, children's book, early reader, chapter book, novel) or runs /make-book.
---

# Make a book with BukuStudio

`PLUGIN` below means the BukuStudio plugin folder: two levels up from this skill's base directory. It contains `engine/`, `wizard/` and `skills/make-book/reference.md` (the file formats every step uses). Run scripts with `python3` (standard library only).

Talk to the user in plain, warm language: they may be a parent or a child. Every choice is made with picture cards in the wizard, never by asking them to type options in chat.

## 1. Start the book

1. Pick a short folder name from the story (for example `mia-and-the-star`), or `my-book` if there is no story yet. Create `books/<name>/` in the current working directory; if it exists, add `-2`, `-3`.
2. If the user already gave a story or author name in chat, write them into `books/<name>/book-settings.json` as `{"story": ..., "author": ...}` so the wizard opens with them filled in.

## 2. Visual setup wizard

1. Run `python3 PLUGIN/engine/serve.py --book books/<name>` in the background. It prints the page URL and opens it in the browser.
2. Tell the user, in one or two sentences, that a page opened where they choose everything by tapping pictures, and give the URL in case it didn't open. Then wait: the command exits by itself when they press "Make my book" (or after an hour idle, printing `{"timeout": true}`; then offer to reopen it).
3. Run `python3 PLUGIN/engine/settings.py books/<name>/book-settings.json --write`. If it reports `errors`, reopen the wizard. Mention any `warnings` to the user briefly.

If the user asked for no wizard ("just use the defaults"), skip to step 3 of this section: `settings.py --write` fills every choice with the recommended one.

## 3. Write the book

Run these agents in order, one at a time. Give each the absolute book folder path and the absolute path of `PLUGIN/skills/make-book/reference.md`.

1. **story-analyst** writes `story-analysis.json`. If `age_fit.ok` is false, tell the user what it found and ask how they'd like to handle it before going on.
2. **author-editor** writes `manuscript.json`.
3. **title-marketing** writes `listing.json`.

Between agents, tell the user in one short line what's happening ("Reading your story…", "Writing the pages…", "Thinking of titles…").

## 4. Checkpoint 1: title and words

If `mode` is `auto`, set `listing.json`'s `chosen` to the first title option and skip to step 5.

Otherwise:

1. Delete any old `review.json`, then run `python3 PLUGIN/engine/serve.py --book books/<name> --page review` in the background. Tell the user a page opened where they pick a title and read every page, and can fix words right there or ask for changes. Wait for it to exit.
2. Run `python3 PLUGIN/engine/apply_review.py books/<name>`. It applies their edits and title choice.
3. If `approved` is false and `notes` is not empty, run **author-editor** again (it reads `review.json` notes), and **title-marketing** too if the notes mention the title or listing. If `notes` is empty, their edits are already applied. Either way, repeat this checkpoint.

## 5. Pictures

Run `python3 PLUGIN/engine/bootstrap.py` first. It installs the print and image libraries the first time (tell the user it's a one-time setup) and prints the Python to use; call it `PY`. `ILL` below means `PY PLUGIN/engine/illustrate.py`.

**An image service is optional.** `ILL mode books/<name>` says how pictures will be made: `pictures_by` is `claude` when there's no key (or the style is Simple shapes), otherwise the service's name. Keys come from `.env` in the working folder, `~/.config/bukustudio/.env`, or the plugin folder (`OPENAI_API_KEY` or `GEMINI_API_KEY`, optionally `BUKU_IMAGE_PROVIDER`). Without one, Claude draws every picture itself; don't ask the user for a key. Mention once, briefly, that adding one later enables painted pictures. Never ask for or handle key values.

**Claude-drawn pictures.** Whenever `ILL refs` or `ILL slots` returns a non-empty `for_claude` list, run **vector-artist** (give it the book folder, the reference.md path and `PLUGIN/assets/svg-kit/kit.svg`); it draws every job in `art/claude-jobs.json`. Then run the same `ILL` command again: it renders the drawings for print and reports them under `made`. Treat "run, draw, run again" as one step below.

1. **Their drawings.** If `drawings` is `some`, or the user mentions drawings, run `python3 PLUGIN/engine/serve.py --book books/<name> --page studio` in the background. Tell them a page opened where they add photos of their drawings (characters, cover, any page) and choose how to use each one. Wait for it to exit.
2. **Plan.** Run **art-director** (give it the book folder and the reference.md path). It writes `art-plan.json`.
3. **Characters and samples.** Run `ILL refs books/<name>`, then `ILL slots books/<name> --sample`.
4. **Check.** Run **consistency-checker**. If any slot failed, run `ILL slots books/<name> --redo` and check again, at most twice; leave what still fails for the user to judge.
5. **Checkpoint 2, style.** If `mode` is `checkpoints`: run `python3 PLUGIN/engine/serve.py --book books/<name> --page pictures` in the background and tell the user to look at the characters and first pictures. When it exits, run `ILL review books/<name>`. If it returns `redo_characters`, run `ILL refs books/<name> --redo`; if `redo_slots`, run `ILL slots books/<name> --redo`; check them and open the page again. Repeat until it returns `approved: true`.
6. **The rest.** Tell the user how many pictures are left and who will make them (Claude, or the image service). Run `ILL slots books/<name>`, then the check-and-redo loop from step 4.
7. **Checkpoint 2, every picture.** If `mode` is `checkpoints`, open the pictures page again and loop as in step 5 until approved. In `auto` mode, skip both checkpoints.
8. Run `ILL disclosure books/<name>` to fill in the AI-disclosure answer for images.

If the image service returns errors (listed under `errors`), explain them plainly. A declined prompt usually needs a gentler brief: edit that slot's `brief` in `art-plan.json` and retry with `--only <slot>`.

## 6. Print files

1. Use the `PY` from step 5 (or run `bootstrap.py` now if you skipped pictures).
2. Run `PY PLUGIN/engine/print_book.py books/<name>`. It builds `print/interior.pdf`, `print/cover.pdf` (paperback or hardcover wrap; not for eBook only), `print/kindle-cover.jpg` and `print/kindle.epub` (fixed layout for picture books, reflowable for chapter books and novels), runs the KDP preflight, and renders proof images (`print/preview-interior.png`, `print/preview-cover.png`).
3. If it reports `errors`, explain each in plain words and fix what you can: text that doesn't fit means asking **author-editor** to shorten those pages, then running this step again. Rules like page counts or hardcover need the user's choice: reopen the wizard.
4. Show the user the two preview images.

Any picture that's missing is drawn as a placeholder; preflight lists those pages. A warning that pictures were enlarged means they may look soft in print: mention it, and suggest a higher-resolution image model if it's large.

## 7. Wrap up

Tell the user what's ready: the chosen title, the number of pages or chapters, the word count, the files and where they are, and any preflight warnings. Then tell them which file goes where in KDP:

| KDP asks for | File |
|---|---|
| Title, description, keywords, categories, age range, AI questions | `listing.json` |
| Paperback or hardcover manuscript / cover | `print/interior.pdf` / `print/cover.pdf` |
| Kindle eBook manuscript / cover | `print/kindle.epub` / `print/kindle-cover.jpg` |

Remind them to order a printed proof before publishing, to check a hardcover cover against KDP's cover calculator, and to open the eBook in Kindle Previewer.
