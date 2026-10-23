"""Hitung metrik dari pengukuran nyata. Tidak menghasilkan skor/partisipan buatan."""
import argparse
import csv
import json
import statistics
from pathlib import Path


def percentile(data, q):
    if not data:
        return None
    data = sorted(data)
    index = (len(data) - 1) * q
    lo = int(index)
    hi = min(lo + 1, len(data) - 1)
    return data[lo] + (data[hi] - data[lo]) * (index - lo)


def evaluate(rows, threshold):
    eligible = [r for r in rows if r.get("quality_pass") == "1" and r.get("cosine_score")]
    genuine = [r for r in eligible if r["comparison"] == "genuine"]
    impostor = [r for r in eligible if r["comparison"] == "impostor"]
    times = [float(r["latency_ms"]) for r in rows if r.get("latency_ms")]
    observed_logins = [r for r in rows if r.get("session_opened") in ("0", "1")]
    return {"threshold_locked": threshold, "attempts": len(rows),
            "participants": len({r["participant_code"] for r in rows}),
            "eligible_genuine": len(genuine), "eligible_impostor": len(impostor),
            "FMR": sum(float(r["cosine_score"]) >= threshold for r in impostor) / len(impostor) if impostor else None,
            "FNMR": sum(float(r["cosine_score"]) < threshold for r in genuine) / len(genuine) if genuine else None,
            "quality_failures": sum(r.get("quality_pass") == "0" for r in rows),
            "challenge_failures": sum(r.get("quality_pass") == "1" and r.get("challenge_pass") == "0" for r in rows),
            "observed_login_outcomes": len(observed_logins),
            "login_success_rate": sum(r["session_opened"] == "1" for r in observed_logins) / len(observed_logins) if observed_logins else None,
            "auth_latency_p50_ms": percentile(times, .5), "auth_latency_p95_ms": percentile(times, .95),
            "PAD_APCER_BPCER": "tidak dihitung; memerlukan definisi dan protokol data PAD khusus"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--threshold", required=True, type=float)
    p.add_argument("--split", choices=["calibration", "test"], required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("Belum ada percobaan; tidak membuat hasil fiktif.")
    for r in rows:
        if r["capture_session"] == r["enrollment_session"]:
            raise SystemExit("Sesi enrollment dan evaluasi harus berbeda")
        if r["split"] != args.split:
            raise SystemExit("File harus hanya memuat satu split yang dipilih")
    args.out.write_text(json.dumps(evaluate(rows, args.threshold), indent=2) + "\n")


if __name__ == "__main__":
    main()
