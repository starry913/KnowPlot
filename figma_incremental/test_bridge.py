"""Exercise the local scene endpoint and CORS behavior."""
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

from bridge import HERE, handler_for


scene = HERE / "scene.example.json"
preview = HERE / "test-bridge-preview.png"
server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(scene, preview))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    url = f"http://127.0.0.1:{server.server_port}/scene"
    with urllib.request.urlopen(url) as response:
        assert response.read() == scene.read_bytes()
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert response.headers["Cache-Control"] == "no-store"
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/health") as response:
        assert response.read() == b"ok"
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/asset/missing.png")
        raise AssertionError("missing asset should be rejected")
    except urllib.error.HTTPError as error:
        assert error.code == 404
    request = urllib.request.Request(url, method="OPTIONS")
    with urllib.request.urlopen(request) as response:
        assert response.status == 204
        assert response.headers["Access-Control-Allow-Private-Network"] == "true"
    png = b"\x89PNG\r\n\x1a\n" + b"test"
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/preview",
        data=png,
        headers={"Content-Type": "image/png"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        assert response.status == 204
    assert preview.read_bytes() == png
finally:
    server.shutdown()
    server.server_close()
    preview.unlink(missing_ok=True)
print("local bridge tests passed")
