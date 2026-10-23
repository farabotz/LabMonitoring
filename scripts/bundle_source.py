"""Source archive hanya file Git yang tidak di-ignore; gagal bila secret path terselip."""
from pathlib import Path
import hashlib
import os
import subprocess
import zipfile

files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
target = Path("dist/LabAccess-source-0.1.0.zip")
target.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
    for name in filter(None, files):
        p = Path(name)
        if name == ".env" or name.startswith((".runtime/", ".tools/", ".venv/")) or p.suffix.lower() in (".key", ".pem", ".dpapi", ".dump", ".onnx"):
            raise RuntimeError("Path sensitif masuk daftar Git: " + name)
        if p.is_file():
            bundle.write(p, "LabAccess/" + name)
print(target)
artifacts = [target, *sorted(Path("dist").glob("*-Setup-*.exe"))]
artifacts += [Path(f"build/{app}/entry_{app}.dist/LabAccess-{app}.exe") for app in ("student", "admin")]
checksums = []
for path in artifacts:
    if path.is_file():
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        name = os.path.relpath(path, "dist").replace("\\", "/")
        checksums.append(f"{digest}  {name}")
Path("dist/SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
print("dist/SHA256SUMS.txt")
