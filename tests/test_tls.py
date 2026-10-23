import os
import socket
import subprocess
import sys
import time
import httpx
import pytest
from packages.desktop.common import Api
from scripts.create_pilot_tls import generate


def test_live_https_certificate_validation(system, tmp_path):
    app, _ = system
    ca, _, cert, key = generate(tmp_path / "tls", "localhost")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cfg = app.state.settings
    env = dict(os.environ, LABACCESS_DATABASE_URL=cfg.database_url,
               LABACCESS_SIGNING_KEY=cfg.signing_key.get_secret_value(), LABACCESS_BIOMETRIC_KEY=cfg.biometric_key.get_secret_value())
    with (tmp_path / "tls-server.log").open("w") as log:
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.api.main:create_app", "--factory", "--host", "127.0.0.1", "--port", str(port),
                              "--ssl-certfile", str(cert), "--ssl-keyfile", str(key), "--no-access-log"], env=env, stdout=log, stderr=log,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        try:
            api = Api(f"https://127.0.0.1:{port}", str(ca))
            for _ in range(100):
                try:
                    result = api.request("GET", "/health")
                    break
                except RuntimeError:
                    time.sleep(.1)
            else:
                pytest.fail("HTTPS server tidak siap")
            assert result["status"] == "ok"
            with pytest.raises(RuntimeError, match="TLS gagal"):
                Api(api.url).request("GET", "/health")
        finally:
            p.terminate()
            p.wait(timeout=15)
