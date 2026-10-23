import threading
import uuid
import pytest


def test_named_pipe_acl_and_allowlist():
    pytest.importorskip("win32pipe")
    from services.windows_agent.bridge import PipeServer, current_sid, pipe_request
    from packages.desktop.common import Api
    api = Api()
    api.device = {"device_id": str(uuid.uuid4()), "name": "TEST-PC", "device_secret": "must-never-leak"}
    name = "LabAccess-test-" + uuid.uuid4().hex
    server = PipeServer(name, current_sid(), api)
    thread = threading.Thread(target=server.serve, daemon=True)
    thread.start()
    try:
        import time
        for _ in range(50):
            try:
                metadata = pipe_request(name, {"op": "metadata"})
                break
            except Exception as exc:
                error = str(exc)
                time.sleep(0.05)
        else:
            pytest.fail("Named pipe tidak tersedia: " + error + " server=" + str(server.last_error))
        assert metadata["name"] == "TEST-PC"
        assert "device_secret" not in metadata
        # Klien lambat harus menerima respons meski server sudah selesai menulis.
        # Tanpa flush, DisconnectNamedPipe dapat membuang respons (error 233).
        import json
        import win32file, win32pipe, win32con
        path = "\\\\.\\pipe\\" + name
        import pywintypes
        deadline = time.monotonic() + 5
        while True:
            try:
                win32pipe.WaitNamedPipe(path, 500)
                handle = win32file.CreateFile(path, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                                             0, None, win32con.OPEN_EXISTING, 0, None)
                break
            except pywintypes.error as exc:
                if exc.winerror not in (2, 231, 121) or time.monotonic() >= deadline:
                    raise
                time.sleep(.03)
        try:
            win32file.WriteFile(handle, json.dumps({"op": "metadata"}).encode())
            time.sleep(.15)
            _, payload = win32file.ReadFile(handle, 4096)
            assert json.loads(payload)["result"]["name"] == "TEST-PC"
        finally:
            win32file.CloseHandle(handle)
        with pytest.raises(RuntimeError, match="tidak diizinkan"):
            pipe_request(name, {"method": "GET", "path": "/admin/users"})
    finally:
        server.stop()
        thread.join(timeout=6)
        assert not thread.is_alive()
