"""Inventaris metadata dan salinan teks lisensi dari dependency terpasang."""
import importlib.metadata as md
import json
from pathlib import Path
import shutil
import sys
import hashlib


def main():
    root = Path("third_party/licenses")
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for dist in sorted(md.distributions(), key=lambda x: x.metadata["Name"].lower()):
        name, version = dist.metadata["Name"], dist.version
        entries.append({"name": name, "version": version, "license_expression": dist.metadata.get("License-Expression"),
                        "license": dist.metadata.get("License"), "homepage": dist.metadata.get("Home-page"),
                        "project_urls": dist.metadata.get_all("Project-URL") or []})
        for file in dist.files or []:
            if any(token in str(file).lower() for token in ("license", "copying", "notice")) and str(file).lower().endswith((".txt", ".md", "license", "copying", "notice", ".rst")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = root / name / Path(file).name
                    target.parent.mkdir(exist_ok=True)
                    if target.exists() and target.read_bytes() != source.read_bytes():
                        raw = source.read_bytes()
                        if any(p.is_file() and p.read_bytes() == raw for p in target.parent.iterdir()):
                            continue
                        target = target.with_name(target.stem + "-" + hashlib.sha256(raw).hexdigest()[:10] + target.suffix)
                    shutil.copyfile(source, target)
    Path("docs/DEPENDENCIES.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Notice runtime/interpreter dan stub installer di luar metadata wheel.
    extra = [(Path(sys.base_prefix) / "LICENSE.txt", root / "Python" / "LICENSE.txt"),
             (Path(".tools/nsis/nsis-3.13/COPYING"), root / "NSIS" / "COPYING")]
    for source, target in extra:
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    print("Metadata tersimpan; lisensi setiap komponen/bobot tetap perlu dinilai dari teksnya.")


if __name__ == "__main__":
    main()
