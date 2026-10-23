"""Unduh hanya pada persiapan instalasi. OID LFS menjadi checksum SHA256 terpin."""
import hashlib
import json
from pathlib import Path
import httpx

COMMIT = "48b10fa505aeb51fbd127fc60a5c660040e823b7"
MODELS = [("face_detection_yunet", "face_detection_yunet_2023mar.onnx", "MIT"),
          ("face_recognition_sface", "face_recognition_sface_2021dec.onnx", "Apache-2.0")]


def main():
    root = Path("models")
    root.mkdir(exist_ok=True)
    existing = root / "manifest.json"
    manifest = json.loads(existing.read_text()) if existing.exists() else {"commit": COMMIT, "models": []}
    with httpx.Client(follow_redirects=True, timeout=120) as c:
        for folder, file, license_name in MODELS:
            entry = next((x for x in manifest["models"] if x["file"] == file), None)
            if entry is None:
                source = f"https://raw.githubusercontent.com/opencv/opencv_zoo/{COMMIT}/models/{folder}/{file}"
                r = c.get(source)
                r.raise_for_status()
                expected = next(line.split("sha256:")[1] for line in r.text.splitlines() if line.startswith("oid sha256:"))
                entry = {"file": file, "sha256": expected, "license": license_name,
                         "url": f"https://media.githubusercontent.com/media/opencv/opencv_zoo/{COMMIT}/models/{folder}/{file}"}
                manifest["models"].append(entry)
            path = root / file
            if not path.exists():
                r = c.get(entry["url"])
                r.raise_for_status()
                if hashlib.sha256(r.content).hexdigest() != entry["sha256"]:
                    raise RuntimeError("Checksum unduhan salah: " + file)
                path.write_bytes(r.content)
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError("Checksum model lokal salah: " + file)
            print(file, entry["sha256"])
    existing.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
