"""Provision credential DPAPI atas identitas Windows yang benar-benar akan menjalankan agent."""
import argparse
import getpass
from pathlib import Path
import uuid
from packages.desktop.common import Api, save_secret

p = argparse.ArgumentParser()
p.add_argument("--server", required=True)
p.add_argument("--ca")
p.add_argument("--allowed-sid", required=True)
p.add_argument("--pipe", default="LabAccess-Agent")
p.add_argument("--config", type=Path, required=True)
args = p.parse_args()
if args.config.exists():
    raise SystemExit("Konfigurasi sudah ada; tidak mengganti identitas perangkat diam-diam.")
api = Api(args.server, args.ca or True)
device = api.request("POST", "/devices/enroll", json={"token": getpass.getpass("Token enrollment sekali pakai: "), "device_id": str(uuid.uuid4())})
save_secret(args.config, {"url": args.server, "ca": args.ca, "device": device, "pipe": args.pipe, "allowed_sid": args.allowed_sid})
print("Agent terdaftar. DPAPI hanya dapat dibuka identitas Windows yang membuatnya. Batasi ACL berkas tersebut.")
