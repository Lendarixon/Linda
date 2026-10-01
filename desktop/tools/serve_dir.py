# -*- coding: utf-8 -*-
"""Static file server with Range support (a stand-in for the Hugging Face repository in tests).
    python tools/serve_dir.py DIR PORT"""
import http.server
import os
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
LOG = Path(sys.argv[3]) if len(sys.argv) > 3 else None


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        rel = self.path.lstrip("/").split("?")[0]
        p = Path(os.path.normpath(ROOT / rel))  # no resolve(): the test repo uses a junction for models/
        if ROOT not in p.parents or not p.is_file():
            self.send_error(404)
            return
        size = p.stat().st_size
        start = 0
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            start = int(rng[6:].split("-")[0])
        if LOG:
            with open(LOG, "a") as f:
                f.write(f"{rel} {start}\n")
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(size - start))
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start)
            while chunk := f.read(1 << 20):
                try:
                    self.wfile.write(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    return


http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
