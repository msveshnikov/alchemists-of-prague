"""Serve a folder on http://127.0.0.1:8766 with CORS, for attaching local images to ChatGPT.

    python serve.py <folder-with-images>

Copy public/hop.html into that folder. Then in the built-in browser open
http://127.0.0.1:8766/hop.html?f=<image>.jpg  (see references/05-chatgpt-browser.md).
"""
import functools
import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        super().end_headers()


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8766
    print(f"serving {folder} on http://127.0.0.1:{port}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=folder)).serve_forever()
