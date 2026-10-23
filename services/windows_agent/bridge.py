"""Named pipe Windows lokal. ACL dan impersonasi memisahkan agent dari UI Session 0.

Tidak menyediakan perintah OS/kontrol Veyon. Service hanya meneruskan API sesi PC sendiri.
"""
import json
import threading
import time
import win32api
import win32con
import win32file
import win32pipe
import win32security
import pywintypes
from packages.desktop.common import Api

MAX_MESSAGE = 5_500_000


def current_sid():
    tok = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.ConvertSidToStringSid(win32security.GetTokenInformation(tok, win32security.TokenUser)[0])
    finally:
        tok.Close()


class PipeServer:
    def __init__(self, pipe_name, allowed_sid, api: Api):
        if not pipe_name.startswith("LabAccess-") or not allowed_sid.startswith("S-1-"):
            raise ValueError("Nama pipe/SID tidak valid")
        self.name = "\\\\.\\pipe\\" + pipe_name
        self.allowed_sid, self.api = allowed_sid, api
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.last_error = None

    def serve(self):
        sd = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            f"D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;{self.allowed_sid})", 1)
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR = sd
        while not self.stop_event.is_set():
            pipe = win32pipe.CreateNamedPipe(self.name, win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT | 8,
                1, MAX_MESSAGE, MAX_MESSAGE, 5000, sa)  # 8 = PIPE_REJECT_REMOTE_CLIENTS
            try:
                try:
                    win32pipe.ConnectNamedPipe(pipe, None)
                except pywintypes.error as exc:
                    if exc.winerror != 535:  # ERROR_PIPE_CONNECTED
                        raise
                # Windows impersonates the security context of the last message read.
                _, data = win32file.ReadFile(pipe, MAX_MESSAGE)
                win32security.ImpersonateNamedPipeClient(pipe)
                try:
                    tok = win32security.OpenThreadToken(win32api.GetCurrentThread(), win32con.TOKEN_QUERY, True)
                    sid = win32security.ConvertSidToStringSid(win32security.GetTokenInformation(tok, win32security.TokenUser)[0])
                    tok.Close()
                finally:
                    win32security.RevertToSelf()
                if sid not in (self.allowed_sid, "S-1-5-18"):
                    win32file.WriteFile(pipe, b'{"error":"SID tidak diizinkan"}')
                    win32file.FlushFileBuffers(pipe)
                    continue
                request = json.loads(data)
                try:
                    with self.lock:
                        response = {"result": self.dispatch(request)}
                except Exception as exc:
                    response = {"error": str(exc)}
                win32file.WriteFile(pipe, json.dumps(response).encode())
                # DisconnectNamedPipe membuang data yang belum dibaca klien.
                # Tunggu pembacaan respons; timeout I/O SCM tetap pekerjaan pilot.
                win32file.FlushFileBuffers(pipe)
            except (pywintypes.error, ValueError, KeyError) as exc:
                self.last_error = (type(exc).__name__, getattr(exc, "winerror", None))
            finally:
                try:
                    win32pipe.DisconnectNamedPipe(pipe)
                except pywintypes.error:
                    pass
                win32file.CloseHandle(pipe)

    def dispatch(self, request):
        if request.get("op") == "metadata":
            return {k: self.api.device[k] for k in ("device_id", "name")}
        method, path = request.get("method"), request.get("path")
        allowed = {("GET", "/health"), ("POST", "/sessions/password"), ("POST", "/sessions/logout"),
                   ("POST", "/devices/heartbeat"), ("POST", "/face/challenges"), ("POST", "/sessions/face")}
        if (method, path) not in allowed:
            raise RuntimeError("Operasi agent tidak diizinkan")
        kwargs = {"json": request.get("json")} if "json" in request else {}
        if path == "/sessions/face":
            import base64
            frames = request.get("frames", [])
            if len(frames) != 3:
                raise ValueError("Diperlukan tiga frame")
            kwargs = {"data": request.get("data", {}),
                      "files": [("frames", ("frame.jpg", base64.b64decode(x, validate=True), "image/jpeg")) for x in frames]}
        result = self.api.request(method, path, **kwargs)
        if isinstance(result, dict) and result.get("token"):
            self.api.token = result["token"]
        if path == "/devices/heartbeat" and result.get("session"):
            self.api.token = result["session"]["token"]
        return result

    def stop(self):
        self.stop_event.set()
        try:
            pipe_request(self.name.rsplit("\\", 1)[1], {"op": "metadata"})
        except Exception:
            pass


def pipe_request(name, request):
    path = "\\\\.\\pipe\\" + name
    deadline = time.monotonic() + 5
    while True:
        try:
            win32pipe.WaitNamedPipe(path, max(1, int((deadline - time.monotonic()) * 1000)))
            pipe = win32file.CreateFile(path, win32con.GENERIC_READ | win32con.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
            break
        except pywintypes.error as exc:
            if exc.winerror not in (2, 231, 121) or time.monotonic() >= deadline:
                raise
            time.sleep(.03)
    try:
        win32pipe.SetNamedPipeHandleState(pipe, win32pipe.PIPE_READMODE_MESSAGE, None, None)
        raw = json.dumps(request).encode()
        if len(raw) > MAX_MESSAGE:
            raise ValueError("Permintaan IPC terlalu besar")
        win32file.WriteFile(pipe, raw)
        _, raw = win32file.ReadFile(pipe, MAX_MESSAGE)
        result = json.loads(raw)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]
    finally:
        win32file.CloseHandle(pipe)
