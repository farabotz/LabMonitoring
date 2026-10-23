"""Pemulihan lokal eksplisit. Jalankan hanya oleh pengelola server berwenang."""
import argparse
import getpass
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from services.api.config import Settings
from services.api.models import Audit, User
from services.api.security import hasher

p = argparse.ArgumentParser()
p.add_argument("--account", required=True)
p.add_argument("--reason", required=True)
args = p.parse_args()
secret = getpass.getpass("Password admin baru (min. 12 karakter): ")
if len(secret) < 12 or len(args.reason) < 5:
    raise SystemExit("Password/alasan terlalu pendek")
with Session(create_engine(Settings().database_url)) as s:
    u = s.scalar(select(User).where(User.nim == args.account, User.role == "admin"))
    if not u:
        raise SystemExit("Target admin tidak ditemukan; tidak membuat akun terselubung.")
    u.password_hash, u.active, u.auth_version = hasher.hash(secret), True, u.auth_version + 1
    s.add(Audit(actor="local-recovery", action="admin.recover", target=u.nim, detail=args.reason[:200]))
    s.commit()
print("Password dipulihkan; token admin lama dicabut.")
