"""Serve one local scene JSON to the Figma development plugin, without external access."""
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def handler_for(scene_path: Path, preview_path: Path | None = None):
    preview_path = preview_path or scene_path.with_name("figma-preview.png")

    class Handler(BaseHTTPRequestHandler):
        def cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def do_OPTIONS(self):
            self.send_response(204)
            self.cors()
            self.end_headers()

        def do_GET(self):
            asset_match = re.fullmatch(r"/asset/([a-zA-Z0-9_.-]+\.png)", self.path)
            if self.path not in ("/scene", "/health") and not asset_match:
                self.send_error(404)
                return
            if asset_match:
                asset = scene_path.parent / "assets" / asset_match.group(1)
                try:
                    data = asset.read_bytes()
                except OSError:
                    self.send_error(404, "asset file not found")
                    return
            elif self.path == "/health":
                data = b"ok"
            else:
                try:
                    data = scene_path.read_bytes()
                except OSError:
                    self.send_error(404, "scene file not found")
                    return
            self.send_response(200)
            content_type = "image/png" if asset_match else ("application/json; charset=utf-8" if self.path == "/scene" else "text/plain")
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.cors()
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/preview":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            if size < 8 or size > 15_000_000:
                self.send_error(413, "invalid preview size")
                return
            data = self.rfile.read(size)
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                self.send_error(415, "PNG required")
                return
            preview_path.write_bytes(data)
            self.send_response(204)
            self.cors()
            self.end_headers()

        def log_message(self, fmt, *args):
            print(fmt % args)

    return Handler


def main():
    parser = ArgumentParser()
    parser.add_argument("--scene", type=Path, default=HERE / "scene.json")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    scene = args.scene.resolve(strict=False)
    if scene == HERE / "scene.json" and not scene.exists():
        scene.write_bytes((HERE / "scene.example.json").read_bytes())
    if not scene.is_file():
        parser.error(f"场景文件不存在: {scene}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(scene))
    print(f"Figma 场景服务已启动: http://localhost:{args.port}/scene")
    print(f"读取文件: {scene}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
