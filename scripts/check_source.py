"""Periksa daftar source Git tanpa mencetak nilai secret lokal."""
import json
from pathlib import Path
import subprocess
from dotenv import dotenv_values


def main():
    files = list(filter(None, subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    ).decode().split("\0")))
    cfg = dotenv_values(".env")
    secrets = [str(cfg[k]).encode() for k in ("LABACCESS_SIGNING_KEY", "LABACCESS_BIOMETRIC_KEY")
               if cfg.get(k) and len(str(cfg[k])) >= 24]
    forbidden, found = [], []
    for name in files:
        p = Path(name)
        if name == ".env" or name.startswith((".runtime/", ".tools/", ".venv/", "build/", "dist/")) or p.suffix.lower() in (".key", ".pem", ".dpapi", ".dump", ".onnx"):
            forbidden.append(name)
        if p.is_file() and any(secret in p.read_bytes() for secret in secrets):
            found.append(name)
    result = {"files_checked": len(files), "local_secret_values_checked": len(secrets),
              "forbidden_paths": forbidden, "local_secrets_found_in_source": found,
              "scope": "Nilai key .env lokal dan path sensitif; bukan audit seluruh jenis secret."}
    Path("evidence/source-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if forbidden or found:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
