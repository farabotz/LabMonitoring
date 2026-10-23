"""Periksa PE dan smoke launch EXE sungguhan; tidak mengganti ekstensi file."""
import json
from pathlib import Path
import struct
import subprocess
import time
import hashlib
import os
import psutil


def inspect_pe(path):
    with path.open("rb") as f:
        if f.read(2) != b"MZ":
            raise RuntimeError("Bukan PE executable: " + str(path))
        f.seek(0x3C)
        offset = struct.unpack("<I", f.read(4))[0]
        f.seek(offset)
        if f.read(4) != b"PE\0\0":
            raise RuntimeError("PE signature salah")
        machine = struct.unpack("<H", f.read(2))[0]
    return {"file": str(path), "bytes": path.stat().st_size, "machine": hex(machine),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    results = []
    for app in ["student", "admin"]:
        path = Path(f"build/{app}/entry_{app}.dist/LabAccess-{app}.exe").resolve()
        report = inspect_pe(path)
        if report["machine"] != "0x8664":
            raise RuntimeError("Aplikasi harus x64")
        command = [str(path), "--smoke-test"]
        if app == "student":
            command += ["--config", str(Path(".runtime/smoke-unused.dpapi").resolve())]
        started = time.perf_counter()
        process = subprocess.Popen(command, cwd=path.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        probe = psutil.Process(process.pid)
        rss, cpu = [], []
        while process.poll() is None:
            if time.perf_counter() - started > 30:
                process.terminate()  # Hanya proses smoke milik skrip, tanpa enrollment/pekerjaan.
                process.wait(10)
                raise RuntimeError("Smoke EXE timeout: " + app)
            try:
                rss.append(probe.memory_info().rss / 1024**2)
                cpu.append(probe.cpu_percent(None) / (psutil.cpu_count() or 1))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(.1)
        stdout, stderr = process.communicate(timeout=5)
        report.update({"smoke_exit": process.returncode, "smoke_seconds": time.perf_counter() - started,
                       "smoke_peak_rss_mib": max(rss) if rss else None,
                       "smoke_cpu_percent_machine_peak": max(cpu) if cpu else None,
                       "resource_scope": "Startup dan jendela login smoke 2 detik; bukan sesi aktif/steady-state, kamera atau Win11"})
        if process.returncode:
            Path(f"evidence/smoke-{app}-failure.txt").write_bytes(stdout + stderr)
            raise RuntimeError("Smoke EXE gagal: " + app)
        results.append(report)
    for path in Path("dist").glob("*-Setup-*.exe"):
        results.append(inspect_pe(path))
    Path("evidence/artifacts.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
