"""Make a book's pictures from art-plan.json: character reference sheets, then
every page (or chapter) picture and the cover. Uploaded drawings are cleaned up
and kept, lightly improved, or fully redrawn, as the user chose. Finished
pictures are sized for print at 300 DPI.

Two ways to make a picture:
- an image service (OpenAI or Gemini), if a key is set up;
- Claude itself, as SVG (the vector-artist agent): always for the "Simple shapes"
  style and "Simple shapes" redraws, and for everything when there's no service.
  Then `refs` / `slots` write the drawing jobs to art/claude-jobs.json and report
  them as `for_claude`; once the agent has written the SVG files, running the
  same command again renders them for print. Light touch without a service is
  Claude's color layer placed under the child's own pencil lines.

usage: .venv/bin/python engine/illustrate.py mode books/<book>         (which way pictures will be made)
       .venv/bin/python engine/illustrate.py targets books/<book>      (every picture slot and its size)
       .venv/bin/python engine/illustrate.py refs books/<book> [--only mia] [--redo]
       .venv/bin/python engine/illustrate.py slots books/<book> [--sample] [--only page-04,cover] [--redo]
       .venv/bin/python engine/illustrate.py review books/<book>       (apply picture-review.json)
       .venv/bin/python engine/illustrate.py disclosure books/<book>
       add --provider fake|openai|gemini|claude to override .env

Writes art/refs/<id>.png, art/<slot>.png, art/preview/<slot>.jpg, art/status.json.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imaging  # noqa: E402
from images import ImageError, available_service, get_provider, nearest_ratio  # noqa: E402
from layout import art_targets  # noqa: E402

NO_TEXT = "Absolutely no words, letters, numbers, signatures or writing anywhere in the picture."
WORKERS = 3
JOBS = "art/claude-jobs.json"
LONG_SIDE = 1000   # SVG viewBox units on the long side of every Claude-drawn picture


def read(book, name, default=None):
    f = book / name
    return json.loads(f.read_text()) if f.exists() else default


def write(book, name, data):
    f = book / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def finished(book, slot):
    return any((book / "art" / f"{slot}.{ext}").exists() for ext in ("png", "jpg"))


def viewbox(w_in, h_in):
    if w_in >= h_in:
        return f"0 0 {LONG_SIDE} {round(LONG_SIDE * h_in / w_in)}"
    return f"0 0 {round(LONG_SIDE * w_in / h_in)} {LONG_SIDE}"


def save_jobs(book, new_jobs, replace_keys):
    """Keep art/claude-jobs.json as the list of drawings Claude still has to make."""
    jobs = [j for j in read(book, JOBS, []) if j["key"] not in replace_keys] + new_jobs
    write(book, JOBS, jobs)
    return new_jobs


def by_claude(settings, plan_slot, provider):
    """Whether Claude draws this slot as SVG, and as what kind of job."""
    mode = plan_slot.get("improve") or "none"
    if plan_slot.get("upload") and mode == "keep":
        return None
    if mode == "vector" or settings.get("artStyle") == "vector":
        return "picture"
    if provider is not None:
        return None
    return "color-layer" if plan_slot.get("upload") and mode == "light" else "picture"


def composition(slot, settings):
    """Where to leave calm space so printed words stay readable."""
    if slot == "cover":
        return ("Book cover art. Keep the top third simple and uncluttered for the title, and a calm strip along the bottom "
                "for the author's name. Keep the main character large and near the center.")
    if slot.startswith("chapter-"):
        return "A wide chapter-opening picture, centered composition."
    if slot == "page-01":
        return "Title page picture: keep the top edge simple."
    layout = settings["layout"]
    if layout == "fullbleed-box":
        return ("Full-page picture. Keep the bottom third calm and simple (soft ground, grass or sky) because words will be "
                "printed there. Keep faces and important things away from all edges.")
    return "Full picture filling the frame. Keep faces and important things away from the edges."


def character_refs(book, plan, ids):
    out = []
    for cid in ids:
        f = book / "art" / "refs" / f"{cid}.png"
        if f.exists():
            out.append(f)
    return out


def style_anchor(book, status, exclude):
    """The first approved picture, sent along so new pictures match its style."""
    for slot, st in status.items():
        if st.get("approved") and slot != exclude and not st["source"].startswith("upload-keep"):
            f = book / "art" / f"{slot}.png"
            if f.exists():
                return f
    return None


def prompt_for(plan, slot_plan, slot, settings, mode, extra):
    style = plan["style"]
    chars = {c["id"]: c for c in plan["characters"]}
    who = " ".join(f"{chars[c]['name']}: {chars[c]['prompt']}" for c in slot_plan.get("characters", []) if c in chars)
    parts = []
    if mode == "light":
        parts.append("The attached first image is a child's drawing. Keep the child's composition, shapes, proportions and "
                     "every object exactly where they are, and keep it charming and hand-drawn. Clean up stray marks, make the "
                     "lines confident, and color it in this style:")
    elif mode == "full":
        parts.append("The attached first image is a child's drawing. Redraw it as a finished children's picture-book "
                     "illustration with the same characters, poses, objects and layout, so the child recognizes their drawing. Style:")
    else:
        parts.append("A children's picture-book illustration. Style:")
    parts.append(style["prompt"])
    if who:
        parts.append(f"Characters (match the attached reference sheets exactly): {who}")
    if slot_plan.get("brief"):
        parts.append(f"Scene: {slot_plan['brief']}")
    parts.append(composition(slot, settings))
    if style.get("avoid"):
        parts.append("Avoid: " + ", ".join(style["avoid"]) + ".")
    parts.append(NO_TEXT)
    if extra:
        parts.append(f"Important changes from the last try: {extra}")
    return "\n".join(parts)


def make_refs(book, provider, only=None, redo=False):
    plan = read(book, "art-plan.json")
    settings = read(book, "book-settings.json")
    refs_dir = book / "art" / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    done, jobs = {}, []
    claude = provider is None or settings.get("artStyle") == "vector"

    def by_service(ch):
        upload = ch.get("reference")
        refs = []
        if upload and (book / upload).exists():
            clean = refs_dir / f"{ch['id']}-upload.png"
            imaging.clean_scan(book / upload, clean)
            refs.append(clean)
        prompt = (f"Character reference sheet for a children's picture book. {ch['name']}: {ch['prompt']}\n"
                  f"Show the character twice, full body: front view and side view, standing, on a plain white background. "
                  f"Style: {plan['style']['prompt']}\n"
                  + ("Base the character on the attached child's drawing, keeping its key features and colors. " if refs else "")
                  + NO_TEXT)
        out = refs_dir / f"{ch['id']}.png"
        out.write_bytes(provider.generate(prompt, refs, "3:2"))
        imaging.preview(out, refs_dir / f"{ch['id']}.jpg")
        return ch["id"], str(out.relative_to(book))

    chars = [c for c in plan["characters"] if not only or c["id"] in only]
    if claude:
        for ch in chars:
            svg = refs_dir / f"{ch['id']}.svg"
            if svg.exists() and redo:
                n = len(list((book / "art" / "raw").glob(f"ref-{ch['id']}-v*.svg"))) + 1
                (book / "art" / "raw").mkdir(parents=True, exist_ok=True)
                svg.rename(book / "art" / "raw" / f"ref-{ch['id']}-v{n}.svg")
            if svg.exists():
                imaging.render_svg(svg, refs_dir / f"{ch['id']}.png", 6, 4, dpi=200)
                imaging.preview(refs_dir / f"{ch['id']}.png", refs_dir / f"{ch['id']}.jpg")
                done[ch["id"]] = str((refs_dir / f"{ch['id']}.png").relative_to(book))
            else:
                upload = ch.get("reference")
                if upload and (book / upload).exists():
                    imaging.clean_scan(book / upload, refs_dir / f"{ch['id']}-upload.png")
                jobs.append({"key": f"ref-{ch['id']}", "kind": "character", "svg": str(svg.relative_to(book)), "viewBox": viewbox(6, 4),
                             "character": ch["id"], "name": ch["name"], "brief": ch["prompt"],
                             "drawing": f"art/refs/{ch['id']}-upload.png" if upload and (book / upload).exists() else None})
    else:
        with ThreadPoolExecutor(WORKERS) as pool:
            for cid, path in pool.map(by_service, chars):
                done[cid] = path
    save_jobs(book, jobs, {f"ref-{c['id']}" for c in chars})
    review = read(book, "picture-review.json")
    if review:
        for cid in done:
            review.get("characters", {}).pop(cid, None)
        write(book, "picture-review.json", review)
    return {"made": done, "for_claude": jobs}


def make_slots(book, provider, only=None, sample=False, redo=False):
    plan = read(book, "art-plan.json")
    settings = read(book, "book-settings.json")
    targets = art_targets(book)
    status = read(book, "art/status.json", {})
    checks = read(book, "art/checks.json", {})
    review = read(book, "picture-review.json", {}).get("slots", {})
    (book / "art" / "raw").mkdir(parents=True, exist_ok=True)
    (book / "art" / "preview").mkdir(parents=True, exist_ok=True)

    if redo:
        wanted = {s for s, c in checks.items() if not c.get("ok", True)} | {s for s, r in review.items() if r.get("action") == "redo"}
        slots = [s for s in targets if s in wanted]
    elif only:
        slots = [s for s in targets if s in only]
    elif sample:
        slots = [s for s in (plan.get("sample_slots") or list(targets)[:2]) if s in targets and not finished(book, s)]
    else:
        slots = [s for s in targets if not finished(book, s)]

    def one(slot):
        sp = plan["slots"].get(slot, {"brief": targets[slot]["scene"], "characters": []})
        t = targets[slot]
        aspect = nearest_ratio(t["w_in"], t["h_in"])
        upload, mode = sp.get("upload"), sp.get("improve") or "none"
        st = status.get(slot, {"attempts": 0})
        extra = " ".join(x for x in (checks.get(slot, {}).get("fix", "") if not checks.get(slot, {}).get("ok", True) else "",
                                     review.get(slot, {}).get("note", "")) if x)
        attempt = st.get("attempts", 0) + 1
        raw = book / "art" / "raw" / f"{slot}-v{attempt}.png"
        final = book / "art" / f"{slot}.png"
        kind = by_claude(settings, sp, provider)
        if kind:
            return claude_slot(slot, sp, t, st, attempt, kind, extra)
        if upload:
            clean = book / "art" / "raw" / f"{slot}-clean.png"
            imaging.clean_scan(book / upload, clean)
            padded = book / "art" / "raw" / f"{slot}-padded.png"
            imaging.pad_to_aspect(clean, padded, t["w_in"] / t["h_in"])
            if mode == "keep":
                raw = padded
            else:
                refs = [padded] + character_refs(book, plan, sp.get("characters", []))
                raw.write_bytes(provider.generate(prompt_for(plan, sp, slot, settings, mode, extra), refs, aspect))
        else:
            refs = character_refs(book, plan, sp.get("characters", []))
            anchor = style_anchor(book, status, slot)
            if anchor:
                refs.append(anchor)
            raw.write_bytes(provider.generate(prompt_for(plan, sp, slot, settings, "none", extra), refs, aspect))
        enlarged = imaging.fit_for_print(raw, final, t["w_in"], t["h_in"])
        imaging.preview(final, book / "art" / "preview" / f"{slot}.jpg")
        source = f"upload-{mode}" if upload else "generated"
        if provider is None and source != "upload-keep":
            raise ImageError("No image service for this picture.")
        return slot, {"source": source, "provider": provider.name if source != "upload-keep" else None,
                      "model": getattr(provider, "model", None) if source != "upload-keep" else None,
                      "attempts": attempt, "enlarged": enlarged, "original": upload, "approved": False,
                      "raw": str(raw.relative_to(book))}

    def prepared_drawing(slot, sp, t):
        clean = book / "art" / "raw" / f"{slot}-clean.png"
        imaging.clean_scan(book / sp["upload"], clean)
        padded = book / "art" / "raw" / f"{slot}-padded.png"
        imaging.pad_to_aspect(clean, padded, t["w_in"] / t["h_in"])
        return padded

    def claude_slot(slot, sp, t, st, attempt, kind, extra):
        """Render Claude's SVG if it's there; otherwise return a drawing job."""
        upload, mode = sp.get("upload"), sp.get("improve") or "none"
        svg = book / ("art/raw" if kind == "color-layer" else "art") / (f"{slot}-colors.svg" if kind == "color-layer" else f"{slot}.svg")
        redo_now = slot in redo_wanted and not st.get("claude_pending")
        if svg.exists() and redo_now:
            svg.rename(book / "art" / "raw" / f"{slot}-v{st.get('attempts', 0)}.svg")
        padded = prepared_drawing(slot, sp, t) if upload else None
        if not svg.exists():
            vb = viewbox(t["w_in"], t["h_in"])
            if padded is not None:
                from PIL import Image
                with Image.open(padded) as im:
                    w, h = im.size
                vb = f"0 0 {w} {h}" if kind == "color-layer" else vb
            anchor = next((f"art/{s}.svg" for s, x in status.items() if x.get("approved") and (book / "art" / f"{s}.svg").exists()), None)
            return slot, {**st, "claude_pending": True, "job": {
                "key": slot, "kind": kind, "svg": str(svg.relative_to(book)), "viewBox": vb, "w_in": round(t["w_in"], 3),
                "h_in": round(t["h_in"], 3), "brief": sp.get("brief", ""), "characters": sp.get("characters", []),
                "drawing": str(padded.relative_to(book)) if padded is not None else None, "note": extra or None,
                "style_reference": anchor, "text_space": composition(slot, settings)}}
        final = book / "art" / f"{slot}.png"
        if kind == "color-layer":
            colors = book / "art" / "raw" / f"{slot}-colors.png"
            from PIL import Image
            with Image.open(padded) as im:
                pw, ph = im.size
            imaging.render_svg(svg, colors, pw / 100, ph / 100, dpi=100)
            raw = book / "art" / "raw" / f"{slot}-v{attempt}.png"
            imaging.color_under_lines(padded, colors, raw)
            enlarged = imaging.fit_for_print(raw, final, t["w_in"], t["h_in"])
        else:
            imaging.render_svg(svg, final, t["w_in"], t["h_in"])
            raw, enlarged = svg, 1
        imaging.preview(final, book / "art" / "preview" / f"{slot}.jpg")
        source = f"upload-{mode}" if upload else "claude"
        return slot, {"source": source, "provider": "claude", "model": None, "attempts": attempt,
                      "enlarged": enlarged, "original": upload, "approved": False, "raw": str(raw.relative_to(book))}

    redo_wanted = set(slots) if redo else set()
    results, errors, jobs = {}, {}, []
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(one, s): s for s in slots}
        for fut, slot in futures.items():
            try:
                s, st = fut.result()
            except ImageError as e:
                errors[slot] = str(e)
                continue
            if st.get("claude_pending"):
                jobs.append(st.pop("job"))
                status[s] = {k: v for k, v in st.items() if k != "job"}
            else:
                results[s] = st
    status.update(results)
    full_review = read(book, "picture-review.json")
    for slot in results:
        checks.pop(slot, None)
        if full_review:
            full_review.get("slots", {}).pop(slot, None)   # its redo note has been used
    write(book, "art/status.json", status)
    write(book, "art/checks.json", checks)
    if full_review:
        write(book, "picture-review.json", full_review)
    save_jobs(book, jobs, set(slots))
    return {"made": sorted(results), "for_claude": jobs, "errors": errors,
            "images_requested": sum(1 for s in results.values() if s.get("provider") not in (None, "claude"))}


def apply_review(book):
    """Apply picture-review.json: accepted pictures are approved, 'original' switches
    an upload to the clean-up of the author's drawing (remade without AI), and
    'redo' notes are picked up by the next `slots --redo` / `refs --redo` run."""
    review = read(book, "picture-review.json", {})
    plan = read(book, "art-plan.json")
    status = read(book, "art/status.json", {})
    redo_slots, redo_chars = [], []
    for slot, r in review.get("slots", {}).items():
        action = r.get("action")
        if action == "accept" and slot in status:
            status[slot]["approved"] = True
        elif action == "original" and slot in plan["slots"]:
            plan["slots"][slot]["improve"] = "keep"
            redo_slots.append(slot)
        elif action == "redo":
            redo_slots.append(slot)
    for cid, r in review.get("characters", {}).items():
        if r.get("action") == "redo":
            redo_chars.append(cid)
            for ch in plan["characters"]:
                if ch["id"] == cid and r.get("note"):
                    ch["prompt"] += f" ({r['note']})"
    for slot in redo_slots:
        if slot in status:
            status[slot]["approved"] = False
    write(book, "art-plan.json", plan)
    write(book, "art/status.json", status)
    return {"approved": bool(review.get("approved")) and not redo_slots and not redo_chars,
            "redo_slots": redo_slots, "redo_characters": redo_chars, "notes": review.get("notes", "")}


def disclosure(book):
    """Fill listing.json's AI-disclosure answer for images from how each picture was made.
    Our reading of KDP's terms: AI-generated = an AI tool created the image (even from a
    sketch); AI-assisted = the person made it and AI only refined it."""
    status = read(book, "art/status.json", {})
    sources = {st["source"] for st in status.values()}
    if sources & {"generated", "claude", "upload-full", "upload-vector"}:
        answer, note = "AI-generated", "Some pictures were created by an AI image tool or drawn by Claude."
    elif "upload-light" in sources:
        answer, note = "AI-assisted", "The pictures were drawn by the author; AI only cleaned up and colored them."
    else:
        answer, note = "none", "All pictures are the author's own drawings, only cleaned up."
    listing = read(book, "listing.json")
    listing.setdefault("ai_disclosure", {})
    listing["ai_disclosure"]["images"] = answer
    listing["ai_disclosure"]["images_note"] = note
    write(book, "listing.json", listing)
    return {"images": answer, "note": note}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["mode", "targets", "refs", "slots", "review", "disclosure"])
    ap.add_argument("book")
    ap.add_argument("--only", default="")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--provider")
    a = ap.parse_args()
    book = Path(a.book)
    simple = {"targets": lambda: {k: {**v, "w_in": round(v["w_in"], 3), "h_in": round(v["h_in"], 3)} for k, v in art_targets(book).items()},
              "review": lambda: apply_review(book), "disclosure": lambda: disclosure(book)}
    if a.command in simple:
        print(json.dumps(simple[a.command](), indent=2, ensure_ascii=False))
        return
    service = None if a.provider == "claude" else (a.provider or available_service())
    if a.command == "mode":
        settings = read(book, "book-settings.json", {})
        print(json.dumps({"service": service, "pictures_by": "claude" if service is None or settings.get("artStyle") == "vector" else service}))
        return
    try:
        provider = get_provider(service) if service else None
    except ImageError as e:
        sys.exit(str(e))
    by = {"provider": provider.name if provider else "claude", "model": getattr(provider, "model", None)}
    only = {s.strip() for s in a.only.split(",") if s.strip()} or None
    if a.command == "refs":
        if a.redo:
            only = {c for c, r in read(book, "picture-review.json", {}).get("characters", {}).items() if r.get("action") == "redo"}
        print(json.dumps({**make_refs(book, provider, only, a.redo), **by}, indent=2))
    else:
        print(json.dumps({**make_slots(book, provider, only, a.sample, a.redo), **by}, indent=2))


if __name__ == "__main__":
    main()
