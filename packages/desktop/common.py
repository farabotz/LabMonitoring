import json
import os
import sys
import ssl
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

STYLE = """
QWidget { background: #f3f6fa; color: #142a43; font: 10pt 'Segoe UI'; }
QLineEdit, QComboBox, QDateTimeEdit { background: white; padding: 9px; border: 1px solid #bac9d9; border-radius: 5px; }
QPushButton { background: #155c88; color: white; padding: 9px 14px; border-radius: 5px; }
QPushButton:disabled { background: #93a6b7; }
QPushButton:hover { background: #21749f; }
QTableWidget { background: white; gridline-color: #dee6ee; }
QHeaderView::section { background: #dce8f3; padding: 8px; border: none; }
QTabBar::tab { padding: 10px 20px; } QGroupBox { margin-top: 10px; padding: 15px; }
"""


def state_path(kind="student"):
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "LabAccess" / kind
    root.mkdir(parents=True, exist_ok=True)
    return root / "device.dpapi"


def save_secret(path: Path, data: dict):
    if sys.platform != "win32":
        raise RuntimeError("Penyimpanan credential desktop memerlukan Windows DPAPI.")
    import win32crypt
    payload = win32crypt.CryptProtectData(json.dumps(data).encode(), "LabAccess", None, None, None, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    # DPAPI current user; no secret-bearing plaintext configuration file.


def load_secret(path):
    if not path.exists():
        return {}
    import win32crypt
    return json.loads(win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1])


class Api:
    def __init__(self, url="http://127.0.0.1:8000", ca=True):
        u = urlsplit(url)
        if u.scheme not in ("http", "https") or (u.scheme == "http" and u.hostname not in ("localhost", "127.0.0.1", "::1")):
            raise ValueError("Alamat server LAN harus menggunakan https:// dan CA tepercaya.")
        self.url, self.ca = url.rstrip("/"), ca
        self.device, self.token = {}, ""

    def request(self, method, path, *, raw=False, **kwargs):
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if self.device:
            headers.update({"X-Device-Id": self.device["device_id"], "X-Device-Secret": self.device["device_secret"]})
        try:
            verify = ssl.create_default_context(cafile=self.ca) if isinstance(self.ca, str) else self.ca
            with httpx.Client(base_url=self.url, verify=verify, timeout=25, trust_env=False) as c:
                r = c.request(method, path, headers=headers, **kwargs)
            if not r.is_success:
                try:
                    detail = r.json().get("detail", "Permintaan gagal")
                except ValueError:
                    detail = "Permintaan gagal (" + str(r.status_code) + ")"
                raise RuntimeError(str(detail))
            return r.content if raw else r.json()
        except httpx.HTTPError:
            raise RuntimeError("Server tidak tersedia/TLS gagal. Periksa koneksi atau hubungi admin.")


class Signals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn, self.signals = fn, Signals()

    def run(self):
        try:
            self.signals.result.emit(self.fn())
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class Jobs:
    def __init__(self):
        self.pending = set()

    def run(self, fn, done, error, finished=None):
        job = Job(fn)
        self.pending.add(job)
        job.signals.result.connect(done)
        job.signals.error.connect(error)
        def cleanup():
            self.pending.discard(job)
            if finished:
                finished()
        job.signals.finished.connect(cleanup)
        QThreadPool.globalInstance().start(job)


def button(label, callback):
    b = QPushButton(label)
    b.clicked.connect(callback)
    return b


def title(text):
    label = QLabel(text)
    label.setStyleSheet("font-size: 23px; font-weight: 700; color: #0b476b; padding: 8px 0;")
    return label


def run_window(window, smoke=False):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = window()
    win.show()
    if smoke:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, app.quit)
    sys.exit(app.exec())
