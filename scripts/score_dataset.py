"""Inferensi offline pada dataset berizin; tidak membuka sesi atau menyimpan embedding."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from packages.face_verification.engine import FaceEngine


def load_dataset(path, split, threshold, lock_path=None):
    path = Path(path).resolve(strict=True)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    people = data.get("participants", {})
    attempts = [a for a in data.get("attempts", []) if a.get("split") == split]
    if not people or not attempts:
        raise ValueError("Dataset belum berisi enrollment dan percobaan; tidak membuat hasil fiktif.")
    for code, p in people.items():
        if p.get("consent_confirmed") is not True or p.get("identity_checked") is not True:
            raise ValueError("Persetujuan dan pemeriksaan identitas belum dicatat: " + code)
        if not p.get("enrollment_session"):
            raise ValueError("Sesi enrollment wajib dicatat.")
    def frames(record):
        paths = [(path.parent / p).resolve(strict=True) for p in record.get("frames", [])]
        if len(paths) != 3 or any(not p.is_relative_to(path.parent) or not p.is_file() for p in paths):
            raise ValueError("Tepat tiga file sampel relatif di direktori dataset diperlukan.")
        if any(p.stat().st_size > 1_500_000 for p in paths):
            raise ValueError("Frame melampaui batas 1,5 MB.")
        return paths
    enroll_frames = {code: frames(p) for code, p in people.items()}
    hash_cache = {}
    def hashes(paths):
        for p in paths:
            if p not in hash_cache:
                hash_cache[p] = hashlib.sha256(p.read_bytes()).hexdigest()
        return {hash_cache[p] for p in paths}
    enrolled = set().union(*(hashes(raw) for raw in enroll_frames.values()))
    split_hashes = {"calibration": set(), "test": set()}
    split_sessions = {"calibration": set(), "test": set()}
    prepared = []
    for a in data.get("attempts", []):
        if a.get("split") not in split_hashes or a.get("direction") not in ("left", "right"):
            raise ValueError("Split atau arah tantangan tidak sah.")
        if a.get("participant_code") not in people or a.get("claimed_code") not in people:
            raise ValueError("Identitas percobaan harus menggunakan kode peserta berizin.")
        session = a.get("capture_session")
        if not session or session in {p["enrollment_session"] for p in people.values()}:
            raise ValueError("Sesi enrollment dan evaluasi harus terpisah.")
        raw = frames(a)
        h = hashes(raw)
        if h & enrolled:
            raise ValueError("Frame enrollment dipakai ulang dalam evaluasi.")
        split_hashes[a["split"]].update(h)
        split_sessions[a["split"]].add(session)
        if a["split"] == split:
            prepared.append((a, raw))
    if split_hashes["calibration"] & split_hashes["test"] or split_sessions["calibration"] & split_sessions["test"]:
        raise ValueError("Frame atau sesi calibration/test tumpang tindih.")
    if split == "test":
        if not lock_path:
            raise ValueError("Pengujian akhir memerlukan berkas threshold yang sudah dikunci.")
        lock = json.loads(Path(lock_path).read_text(encoding="utf-8-sig"))
        if lock.get("status") != "locked" or lock.get("threshold") != threshold or not lock.get("locked_at") or not lock.get("approved_by"):
            raise ValueError("Threshold belum dikunci atau berbeda dari konfigurasi uji.")
        if set(lock.get("calibration_sessions", [])) & split_sessions["test"]:
            raise ValueError("Sesi uji akhir pernah dipakai kalibrasi.")
    return people, enroll_frames, prepared


def score(path, split, threshold, models, lock_path=None):
    people, enrollment, attempts = load_dataset(path, split, threshold, lock_path)
    if split == "test":
        lock = json.loads(Path(lock_path).read_text(encoding="utf-8-sig"))
        if lock.get("model_commit") != json.loads((Path(models) / "manifest.json").read_text())["commit"]:
            raise ValueError("Versi model tidak cocok dengan threshold yang dikunci.")
    engine = FaceEngine(Path(models))
    templates = {code: engine.enroll([p.read_bytes() for p in paths]) for code, paths in enrollment.items()}
    rows = []
    for a, paths in attempts:
        raw = [p.read_bytes() for p in paths]
        attack = a.get("attack_type", "none")
        row = {k: a.get(k, "") for k in ("participant_code", "claimed_code", "capture_session", "split", "lighting", "camera_id")}
        row.update(enrollment_session=people[a["claimed_code"]]["enrollment_session"],
                   comparison="attack" if attack != "none" else ("genuine" if a["participant_code"] == a["claimed_code"] else "impostor"),
                   attack_type=attack, quality_pass="0", challenge_pass="", cosine_score="",
                   session_opened="", latency_ms="", inference_ms="", notes="offline; tidak membuka sesi API")
        started = time.perf_counter()
        try:
            samples = [engine.sample(frame)[0] for frame in raw]
            target = np.asarray(templates[a["claimed_code"]]["embedding"])
            row["quality_pass"] = "1"
            row["cosine_score"] = min(float(np.dot(f, target)) for f in samples)
            try:
                # Kebijakan sama dengan produksi. Pass kedua sengaja memakai verify
                # tanpa menyalin logika tantangan; timing dilabeli offline dua pass.
                engine.verify(raw, templates[a["claimed_code"]], a["direction"], threshold)
                row["challenge_pass"] = "1"
            except ValueError as exc:
                if str(exc).startswith("Tantangan gerakan gagal"):
                    row["challenge_pass"] = "0"
                elif str(exc).startswith("Wajah tidak cocok"):
                    row["challenge_pass"] = "1"
                else:
                    raise RuntimeError("Inferensi verifikasi gagal di luar keputusan kualitas/tantangan yang dikenal.") from exc
                row["notes"] += "; " + str(exc)
        except ValueError as exc:
            row["quality_pass"], row["cosine_score"] = "0", ""
            row["notes"] += "; " + str(exc)
        row["inference_ms"] = round((time.perf_counter() - started) * 1000, 3)
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--split", choices=["calibration", "test"], required=True)
    p.add_argument("--threshold", type=float, required=True)
    p.add_argument("--threshold-lock", type=Path)
    p.add_argument("--models", type=Path, default=Path("models"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit("Output sudah ada; tidak ditimpa.")
    if not -1 <= args.threshold <= 1:
        raise SystemExit("Threshold cosine harus antara -1 dan 1.")
    try:
        rows = score(args.manifest, args.split, args.threshold, args.models, args.threshold_lock)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} percobaan offline ditulis. Tidak ada embedding/frame di output.")


if __name__ == "__main__":
    main()
