"""Book settings: fill defaults and validate, using the same rules as the wizard
(wizard/steps.json). wizard/app.js mirrors this logic; keep them in sync.

usage: python3 engine/settings.py books/<book>/book-settings.json [--write]
prints {"settings", "warnings", "errors"}; --write saves the filled settings back.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
STEPS = json.loads((ROOT / "wizard" / "steps.json").read_text())["steps"]
CHOICE_KINDS = {"cards", "multi"}


def matches(cond, s):
    return all(s.get(k) in vals for k, vals in cond.items())


def step_active(step, s):
    return matches(step.get("only_for", {}), s)


def available(step, s):
    return [o for o in step.get("options", []) if matches(o.get("only_for", {}), s)]


def recommended(step, s):
    opts = available(step, s)
    if step["kind"] == "multi":
        return [o["value"] for o in opts if o.get("default_on")]
    values = [o["value"] for o in opts]
    rule = step.get("recommend")
    v = rule["map"].get(str(s.get(rule["by"])), rule.get("else")) if rule else step.get("default")
    return v if v in values else (values[0] if values else None)


def option_warnings(step, value, s):
    out = []
    for o in step.get("options", []):
        if o["value"] != value:
            continue
        for w in o.get("warn", []):
            if "when" in w and matches(w["when"], s):
                out.append(w["text"])
            below = w.get("when_below")
            if below and all(isinstance(s.get(k), (int, float)) and s[k] < n for k, n in below.items()):
                out.append(w["text"])
    return out


def fill(settings):
    """Return (settings, warnings, errors) with every missing or unavailable choice
    replaced by the recommended one."""
    s = dict(settings)
    warnings, errors = [], []
    if not str(s.get("story", "")).strip():
        errors.append("story is required")
    if not str(s.get("author", "")).strip():
        errors.append("author is required")
    s.setdefault("language", "English")
    if s.get("imageService") not in ("available", "none"):
        from images import available_service
        s["imageService"] = "available" if available_service() else "none"
    for step in STEPS:
        if step["kind"] not in CHOICE_KINDS:
            continue
        sid = step["id"]
        if not step_active(step, s):
            s[sid] = None
            continue
        values = [o["value"] for o in available(step, s)]
        if step["kind"] == "multi":
            current = s.get(sid)
            s[sid] = recommended(step, s) if current is None else [v for v in current if v in values]
        else:
            if s.get(sid) not in values:
                s[sid] = recommended(step, s)
            warnings += option_warnings(step, s[sid], s)
    return s, warnings, errors


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    s, warnings, errors = fill(json.loads(path.read_text()))
    if "--write" in sys.argv:
        path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"settings": s, "warnings": warnings, "errors": errors}, indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
