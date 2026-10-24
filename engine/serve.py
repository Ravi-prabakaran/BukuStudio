"""Local server for the visual wizard and the checkpoint review pages.

Opens the page in the browser, lets it read and save files in one book folder,
and exits once the page saves its final answer (so a caller can wait on it).

usage: python3 engine/serve.py --book books/<book> [--page wizard|review|studio|pictures] [--no-open]
"""
import argparse
import json
import mimetypes
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from images import available_service  # noqa: E402

STATIC_DIRS = ("wizard", "assets")
READABLE = {"book-settings.json", "story-analysis.json", "manuscript.json", "listing.json", "review.json",
            "art-choices.json", "art-plan.json", "picture-review.json", "art/status.json", "art/checks.json"}
WRITABLE = {"book-settings.json", "review.json", "art-choices.json", "picture-review.json"}
IMAGE_DIRS = ("uploads/", "art/preview/", "art/refs/")
SLOT = re.compile(r"^(page-\d{2}|chapter-\d{2}|cover|character-[a-z0-9-]{1,40})$")
MAX_UPLOAD = 25 * 1024 * 1024
PAGES = {"wizard": "index.html", "review": "review.html", "studio": "studio.html", "pictures": "pictures.html"}
IDLE_LIMIT = 60 * 60


def image_type(data):
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return None


class Handler(BaseHTTPRequestHandler):
    book: Path
    last_seen = time.time()

    def log_message(self, *args):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        Handler.last_seen = time.time()
        path = self.path.split("?")[0].lstrip("/")
        if path == "api/capabilities":
            # Only whether a service is set up, never anything about the key itself.
            return self.send(200, json.dumps({"image_service": available_service()}))
        if path.startswith("api/image/"):
            rel = path.removeprefix("api/image/")
            f = (self.book / rel).resolve()
            inside = self.book in f.parents and f.relative_to(self.book).as_posix().startswith(IMAGE_DIRS)
            if inside and f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                return self.send(200, f.read_bytes(), "image/png" if f.suffix.lower() == ".png" else "image/jpeg")
            return self.send(404, '{"error":"not found"}')
        if path.startswith("api/file/"):
            name = path.removeprefix("api/file/")
            f = self.book / name
            if name in READABLE and f.exists():
                return self.send(200, f.read_bytes())
            return self.send(404, '{"error":"not found"}')
        f = (ROOT / path).resolve()
        if path.split("/")[0] in STATIC_DIRS and f.is_file() and ROOT in f.parents:
            return self.send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        self.send(404, '{"error":"not found"}')

    def do_DELETE(self):
        Handler.last_seen = time.time()
        slot = self.path.split("?")[0].lstrip("/").removeprefix("api/upload/")
        if not SLOT.match(slot):
            return self.send(404, '{"error":"not found"}')
        for f in (self.book / "uploads").glob(f"{slot}.*"):
            f.unlink()
        self.send(200, '{"ok":true}')

    def upload(self, slot):
        if not SLOT.match(slot):
            return self.send(404, '{"error":"not found"}')
        length = int(self.headers.get("Content-Length", 0))
        if not 0 < length <= MAX_UPLOAD:
            return self.send(413, '{"error":"Pictures must be under 25 MB."}')
        data = self.rfile.read(length)
        ext = image_type(data)
        if not ext:
            return self.send(415, '{"error":"Only JPEG or PNG pictures."}')
        folder = self.book / "uploads"
        folder.mkdir(exist_ok=True)
        for old in folder.glob(f"{slot}.*"):
            old.unlink()
        (folder / f"{slot}.{ext}").write_bytes(data)
        self.send(200, json.dumps({"ok": True, "file": f"uploads/{slot}.{ext}"}))

    def do_POST(self):
        Handler.last_seen = time.time()
        path = self.path.split("?")[0].lstrip("/")
        if path.startswith("api/upload/"):
            return self.upload(path.removeprefix("api/upload/"))
        name = path.removeprefix("api/save/")
        if name not in WRITABLE:
            return self.send(404, '{"error":"not found"}')
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except (ValueError, json.JSONDecodeError):
            return self.send(400, '{"error":"bad json"}')
        final = data.pop("_final", False)
        out = self.book / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        self.send(200, '{"ok":true}')
        if final:
            print(json.dumps({"saved": str(out)}), flush=True)
            threading.Thread(target=self.server.shutdown, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--page", choices=list(PAGES), default="wizard")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    book = Path(args.book).resolve()
    book.mkdir(parents=True, exist_ok=True)
    Handler.book = book
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    page = PAGES[args.page]
    url = f"http://127.0.0.1:{server.server_port}/wizard/{page}"
    print(json.dumps({"url": url, "book": str(book)}), flush=True)

    def idle_watch():
        while True:
            time.sleep(30)
            if time.time() - Handler.last_seen > IDLE_LIMIT:
                print(json.dumps({"timeout": True}), flush=True)
                server.shutdown()
                return

    threading.Thread(target=idle_watch, daemon=True).start()
    if not args.no_open:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
