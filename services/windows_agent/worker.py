"""Agent tanpa UI/kamera. Mode foreground dapat diuji tanpa mengubah service Windows."""
import argparse
import threading
import psutil
from packages.desktop.common import Api, load_secret
from .bridge import PipeServer
from pathlib import Path


def run(config: Path, stop=None):
    # DPAPI current user in foreground; service LocalSystem must enroll under its own identity.
    data = load_secret(config)
    api = Api(data["url"], data.get("ca") or True)
    api.device = data["device"]
    bridge = PipeServer(data.get("pipe", "LabAccess-Agent"), data["allowed_sid"], api)
    event = stop or threading.Event()
    thread = threading.Thread(target=bridge.serve, daemon=True)
    thread.start()
    boot = str(round(psutil.boot_time()))
    interval = 10
    try:
        while not event.is_set():
            try:
                with bridge.lock:
                    r = api.request("POST", "/devices/heartbeat", json={"boot_id": boot})
                    interval = max(3, min(300, r.get("heartbeat_seconds", interval)))
                    if r.get("session"):
                        api.token = r["session"]["token"]
            except RuntimeError:
                pass  # Preserve active session on outage; never terminate Windows applications.
            event.wait(interval)
    finally:
        bridge.stop()
        thread.join(timeout=6)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    args = p.parse_args()
    try:
        run(args.config)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
