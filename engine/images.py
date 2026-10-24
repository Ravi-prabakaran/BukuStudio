"""Image services behind one interface: OpenAI, Gemini, and a "fake" service
that draws stand-in images offline (for tests and dry runs).

Image services are optional. Pick one with BUKU_IMAGE_PROVIDER in .env
(openai | gemini | fake); otherwise the first service with a key is used, and
with no key at all Claude draws the pictures itself (see illustrate.py). BUKU_OPENAI_MODEL and
BUKU_GEMINI_MODEL override the model each service picks automatically.
"""
import base64
import io
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Aspect ratios the services can make, as width / height.
RATIOS = {"1:1": 1.0, "2:3": 2 / 3, "3:2": 1.5, "3:4": 0.75, "4:3": 4 / 3, "9:16": 9 / 16, "16:9": 16 / 9}
OPENAI_SIZES = {"square": "1024x1024", "portrait": "1024x1536", "landscape": "1536x1024"}


def env_files():
    """Where keys may live: the user's working folder, ~/.config/bukustudio, then the plugin folder."""
    return [Path.cwd() / ".env", Path.home() / ".config" / "bukustudio" / ".env", ROOT / ".env"]


def load_env():
    env = dict(os.environ)
    for f in env_files():
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def nearest_ratio(w, h):
    target = w / h
    return min(RATIOS, key=lambda r: abs(RATIOS[r] - target))


def png_bytes(path_or_img, max_side=2048):
    from PIL import Image
    img = path_or_img if hasattr(path_or_img, "save") else Image.open(path_or_img)
    img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class ImageError(RuntimeError):
    pass


class OpenAI:
    name = "openai"

    def __init__(self, key, model=None):
        import requests
        self.http, self.key = requests, key
        self.model = model or self.pick_model()

    def pick_model(self):
        r = self.http.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {self.key}"}, timeout=30)
        r.raise_for_status()
        ids = sorted(m["id"] for m in r.json()["data"] if m["id"].startswith("gpt-image") and "mini" not in m["id"])
        return ids[-1] if ids else "gpt-image-1"

    def generate(self, prompt, refs=(), aspect="1:1"):
        ratio = RATIOS[aspect]
        size = OPENAI_SIZES["square" if 0.9 <= ratio <= 1.1 else "portrait" if ratio < 1 else "landscape"]
        headers = {"Authorization": f"Bearer {self.key}"}
        data = {"model": self.model, "prompt": prompt, "size": size, "quality": "high", "n": "1"}
        if refs:
            files = [("image[]", (f"ref{i}.png", png_bytes(p), "image/png")) for i, p in enumerate(refs)]
            r = self.http.post("https://api.openai.com/v1/images/edits", headers=headers, data=data, files=files, timeout=600)
        else:
            r = self.http.post("https://api.openai.com/v1/images/generations", headers=headers, json=data, timeout=600)
        if not r.ok:
            raise ImageError(f"OpenAI {r.status_code}: {r.text[:400]}")
        return base64.b64decode(r.json()["data"][0]["b64_json"])


class Gemini:
    name = "gemini"
    API = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, key, model=None):
        import requests
        self.http, self.key = requests, key
        self.model = model or self.pick_model()

    def pick_model(self):
        r = self.http.get(f"{self.API}/models", headers={"x-goog-api-key": self.key}, params={"pageSize": 1000}, timeout=30)
        r.raise_for_status()
        names = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
                 if "image" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])]
        pro = sorted(n for n in names if "pro" in n)
        flash = sorted(n for n in names if "flash" in n)
        return (pro or flash or names or ["gemini-2.5-flash-image"])[-1]

    def generate(self, prompt, refs=(), aspect="1:1"):
        parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(png_bytes(p)).decode()}} for p in refs]
        image_config = {"aspectRatio": aspect}
        if "pro" in self.model:
            image_config["imageSize"] = "4K"   # only the Pro image models make large images
        body = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": image_config}}
        r = self.http.post(f"{self.API}/models/{self.model}:generateContent", headers={"x-goog-api-key": self.key}, json=body, timeout=600)
        if not r.ok and "imageSize" in image_config:
            image_config.pop("imageSize")
            r = self.http.post(f"{self.API}/models/{self.model}:generateContent", headers={"x-goog-api-key": self.key}, json=body, timeout=600)
        if not r.ok:
            raise ImageError(f"Gemini {r.status_code}: {r.text[:400]}")
        for cand in r.json().get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                data = part.get("inlineData") or part.get("inline_data")
                if data:
                    return base64.b64decode(data["data"])
        raise ImageError("Gemini returned no image (it may have declined the prompt).")


class Fake:
    """Draws a labeled stand-in image so the pipeline can run without a service."""
    name = "fake"
    model = "fake"

    def generate(self, prompt, refs=(), aspect="1:1"):
        from PIL import Image, ImageDraw
        ratio = RATIOS[aspect]
        w, h = (1024, round(1024 / ratio)) if ratio >= 1 else (round(1024 * ratio), 1024)
        rnd = random.Random(prompt)
        img = Image.new("RGB", (w, h), tuple(rnd.randint(150, 230) for _ in range(3)))
        d = ImageDraw.Draw(img)
        d.ellipse([w * 0.6, h * 0.1, w * 0.8, h * 0.1 + w * 0.2], fill=(250, 199, 117))
        d.rectangle([0, h * 0.7, w, h], fill=(99, 153, 34))
        d.text((20, 20), f"FAKE IMAGE ({len(refs)} refs)\n" + prompt[:160], fill=(30, 30, 30))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()


def available_service():
    """Which image service is set up, without contacting it: 'openai', 'gemini',
    'fake', or None (Claude draws the pictures itself)."""
    env = load_env()
    name = env.get("BUKU_IMAGE_PROVIDER")
    if name == "fake":
        return "fake"
    if name in ("openai", "gemini"):
        return name if env.get(f"{name.upper()}_API_KEY") else None
    return "openai" if env.get("OPENAI_API_KEY") else "gemini" if env.get("GEMINI_API_KEY") else None


def get_provider(name=None):
    env = load_env()
    name = name or env.get("BUKU_IMAGE_PROVIDER") or ("openai" if env.get("OPENAI_API_KEY") else "gemini" if env.get("GEMINI_API_KEY") else None)
    if name == "fake":
        return Fake()
    if name == "openai":
        if not env.get("OPENAI_API_KEY"):
            raise ImageError("OPENAI_API_KEY is missing from .env")
        return OpenAI(env["OPENAI_API_KEY"], env.get("BUKU_OPENAI_MODEL"))
    if name == "gemini":
        if not env.get("GEMINI_API_KEY"):
            raise ImageError("GEMINI_API_KEY is missing from .env")
        return Gemini(env["GEMINI_API_KEY"], env.get("BUKU_GEMINI_MODEL"))
    raise ImageError("No image service set up. Add OPENAI_API_KEY or GEMINI_API_KEY to .env (see .env.example).")
