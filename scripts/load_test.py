"""35 klien simulasi lewat HTTP + PostgreSQL, schema sintetis terisolasi."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid
from cryptography.fernet import Fernet
import httpx
import psutil
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from services.api.models import Base, Device, User
from services.api.security import digest, hasher
from scripts.evaluate_scores import percentile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", required=True)
    p.add_argument("--clients", type=int, default=35, choices=range(1, 101))
    p.add_argument("--out", type=Path, default=Path("evidence/load-35.json"))
    args = p.parse_args()
    parsed = make_url(args.database_url)
    if parsed.get_backend_name() != "postgresql" or not parsed.database.startswith("labaccess_test_"):
        raise SystemExit("Hanya PostgreSQL database labaccess_test_* yang diizinkan")
    control = create_engine(args.database_url)
    schema = "load_" + uuid.uuid4().hex
    with control.begin() as c:
        c.execute(text('CREATE SCHEMA "' + schema + '"'))
    url = parsed.update_query_dict({"options": "-csearch_path=" + schema}).render_as_string(hide_password=False)
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    encoded = hasher.hash(password)
    devices = [(str(uuid.uuid4()), secrets.token_urlsafe(32)) for _ in range(args.clients)]
    with Session(engine) as s:
        s.add(User(nim="load-admin", name="Synthetic Admin", role="admin", password_hash=encoded))
        for i, (device_id, secret) in enumerate(devices):
            s.add(User(nim=f"LOAD{i:03}", name=f"Synthetic {i}", role="student", password_hash=encoded))
            s.add(Device(id=device_id, name=f"LOAD-PC{i:03}", secret_hash=digest(secret)))
        s.commit()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, LABACCESS_DATABASE_URL=url, LABACCESS_SIGNING_KEY=secrets.token_urlsafe(48),
               LABACCESS_BIOMETRIC_KEY=Fernet.generate_key().decode())
    base_url = f"http://127.0.0.1:{port}"
    log = open(Path(".runtime") / "load-api.log", "w")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.api.main:create_app", "--factory",
                                "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                               env=env, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    stop, resource_samples = threading.Event(), []
    def sample_resources():
        proc = psutil.Process(process.pid)
        while not stop.wait(.5):
            try:
                tree = [proc] + proc.children(recursive=True)
                resource_samples.append(sum(x.memory_info().rss for x in tree))
            except psutil.Error:
                pass
    monitor = threading.Thread(target=sample_resources, daemon=True)
    monitor.start()
    try:
        with httpx.Client(base_url=base_url, timeout=120, trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError("API tidak siap")
            admin = client.post("/auth/admin", json={"nim": "load-admin", "password": password})
            admin.raise_for_status()
            headers_admin = {"Authorization": "Bearer " + admin.json()["token"]}
            def one(i):
                d, secret = devices[i]
                headers = {"X-Device-Id": d, "X-Device-Secret": secret}
                start = time.perf_counter()
                r = client.post("/sessions/password", headers=headers,
                                json={"nim": f"LOAD{i:03}", "password": password, "request_key": str(uuid.uuid4())})
                r.raise_for_status()
                login_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                client.post("/devices/heartbeat", headers=headers, json={"boot_id": "load-boot"}).raise_for_status()
                heartbeat_ms = (time.perf_counter() - start) * 1000
                return headers | {"Authorization": "Bearer " + r.json()["token"]}, login_ms, heartbeat_ms
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(min(args.clients, 35)) as pool:
                results = list(pool.map(one, range(args.clients)))
            start = time.perf_counter()
            status = client.get("/admin/devices", headers=headers_admin)
            status.raise_for_status()
            admin_latency = (time.perf_counter() - start) * 1000
            active = sum(d["session"] is not None for d in status.json())
            assert active == args.clients
            for headers, _, _ in results:
                client.post("/sessions/logout", headers=headers).raise_for_status()
            report = {"kind": "simulated_clients_same_host", "physical_lab_pcs": 0,
                      "clients": args.clients, "successful_logins": len(results), "admin_active_sessions": active,
                      "login_p50_ms": percentile([r[1] for r in results], .5),
                      "login_p95_ms": percentile([r[1] for r in results], .95),
                      "heartbeat_p95_ms": percentile([r[2] for r in results], .95),
                      "admin_get_latency_ms": admin_latency, "wall_seconds": time.perf_counter() - started,
                      "server_process_tree_peak_rss_mb": max(resource_samples, default=0) / 1024**2,
                      "note": "Tidak mewakili 35 PC fisik, UI desktop atau beban Veyon/wajah."}
            args.out.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
    finally:
        stop.set()
        process.terminate()
        process.wait(timeout=15)
        monitor.join(timeout=2)
        log.close()
        engine.dispose()
        with control.begin() as c:
            c.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        control.dispose()


if __name__ == "__main__":
    main()
