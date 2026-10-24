"""Compare image services before choosing one: runs the same sketch through
every service with a key, in "Light touch" and "Full redraw" modes plus one
picture made from scratch, and builds a side-by-side page with sizes and timings.

usage: .venv/bin/python engine/image_test.py [drawing] [--out books/test/compare]
       the drawing defaults to a built-in sample pencil sketch
"""
import argparse
import html
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imaging  # noqa: E402
from images import ImageError, get_provider, load_env  # noqa: E402

STYLE = ("Soft, gentle watercolor illustration for a bedtime picture book for ages 3 to 7, loose washes with light pencil "
         "outlines, warm palette, simple background.")
NO_TEXT = "Absolutely no words, letters or numbers in the picture."
TESTS = {
    "light": ("Light touch", True, "The attached image is a child's drawing. Keep the child's composition, shapes and every object "
              f"exactly where they are, keep it charming and hand-drawn. Clean up stray marks and color it. Style: {STYLE} {NO_TEXT}"),
    "full": ("Full redraw", True, "The attached image is a child's drawing. Redraw it as a finished picture-book illustration with "
             f"the same characters, poses, objects and layout, so the child recognizes it. Style: {STYLE} {NO_TEXT}"),
    "scratch": ("From scratch", False, "A small red fox with a green scarf holding a glowing golden star on a moonlit hilltop, "
                f"looking up at the night sky. Keep the bottom third calm for text. Style: {STYLE} {NO_TEXT}"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drawing", nargs="?")
    ap.add_argument("--out", default="books/test/compare")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    drawing = Path(a.drawing) if a.drawing else imaging.sample_sketch(out / "sample-sketch.jpg")
    clean = imaging.clean_scan(drawing, out / "clean.png")
    padded = imaging.pad_to_aspect(clean, out / "padded.png", 1.0)

    env = load_env()
    names = [n for n, k in (("openai", "OPENAI_API_KEY"), ("gemini", "GEMINI_API_KEY")) if env.get(k)]
    if not names:
        sys.exit("No OPENAI_API_KEY or GEMINI_API_KEY found in .env")
    results = []
    for name in names:
        try:
            provider = get_provider(name)
        except Exception as e:  # noqa: BLE001 - report any setup failure and move on
            results.append({"provider": name, "error": str(e)})
            continue
        for key, (label, uses_drawing, prompt) in TESTS.items():
            print(f"{name} ({provider.model}): {label}…", flush=True)
            t0 = time.time()
            try:
                data = provider.generate(prompt, [padded] if uses_drawing else [], "1:1")
                f = out / f"{name}-{key}.png"
                f.write_bytes(data)
                from PIL import Image
                with Image.open(f) as im:
                    size = im.size
                results.append({"provider": name, "model": provider.model, "test": key, "file": f.name, "px": size,
                                "seconds": round(time.time() - t0, 1), "enlarge_for_8.75in": round(8.75 * 300 / size[1], 2)})
            except ImageError as e:
                results.append({"provider": name, "model": provider.model, "test": key, "error": str(e)})

    (out / "results.json").write_text(json.dumps(results, indent=2))
    cells = []
    for r in results:
        if "error" in r:
            cells.append(f'<figure><div class="err">{html.escape(r["error"][:300])}</div><figcaption><b>{r["provider"]} {TESTS.get(r.get("test"), ("",))[0]}</b></figcaption></figure>')
        else:
            cells.append(f'<figure><img src="{r["file"]}"><figcaption><b>{r["provider"]}: {TESTS[r["test"]][0]}</b>'
                         f'<span>{html.escape(r["model"])} · {r["px"][0]}×{r["px"][1]} px · {r["seconds"]} s · enlarge {r["enlarge_for_8.75in"]}× for print</span></figcaption></figure>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Image service test</title><style>
:root{{--bg:#f5f4ef;--card:#fff;--text:#1f1e1b;--muted:#5f5e5a;--line:#e2e0d8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1b1b1a;--card:#30302e;--text:#f1efe8;--muted:#b4b2a9;--line:#3d3d3a}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--text);font-family:system-ui,sans-serif}} main{{max-width:1100px;margin:0 auto}}
.row{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}} figure{{margin:0;background:var(--card);border:.5px solid var(--line);border-radius:12px;padding:10px}}
img{{width:100%;aspect-ratio:1;object-fit:contain;background:#fff;border-radius:8px}} figcaption{{display:flex;flex-direction:column;gap:2px;margin-top:8px;font-size:14px}}
figcaption span{{color:var(--muted);font-size:12px}} b{{font-weight:600}} .err{{aspect-ratio:1;display:flex;align-items:center;padding:10px;color:#a32d2d;font-size:13px}}
</style></head><body><main><h1>Image service test</h1>
<div class="row"><figure><img src="{html.escape(Path(drawing).name) if Path(drawing).parent == out else html.escape(str(Path(drawing).resolve()))}"><figcaption><b>Original sketch</b></figcaption></figure>
<figure><img src="clean.png"><figcaption><b>Keep as is</b><span>Clean-up only, no AI</span></figcaption></figure>{''.join(cells)}</div></main></body></html>"""
    (out / "comparison.html").write_text(page)
    print(json.dumps({"page": str(out / "comparison.html"), "results": results}, indent=2))


if __name__ == "__main__":
    main()
