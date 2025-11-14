#!/usr/bin/env python3
import argparse
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.utils.metrics import get_registry


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # type: ignore[override]
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        payload = get_registry().render_prometheus().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args):  # type: ignore[override]
        # Silence default HTTP server logging; rely on main app logging instead.
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Expose in-process metrics over HTTP for Prometheus scraping.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MetricsHandler)
    print(f"Metrics server listening on http://{args.host}:{args.port}/metrics")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMetrics server stopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

