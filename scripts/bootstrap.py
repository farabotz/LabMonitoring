import argparse
import getpass
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from services.api.config import Settings
from services.api.models import User, Audit
from services.api.security import hasher
from packages.desktop.common import save_secret


def main():
    p = argparse.ArgumentParser(description="Bootstrap tanpa password bawaan. Tidak mereset database.")
    p.add_argument("--init-env", action="store_true")
    p.add_argument("--demo", action="store_true", help="Akun sintetis + password acak disimpan DPAPI")
    p.add_argument("--admin", default="admin")
    args = p.parse_args()
    if args.init_env:
        env = Path(".env")
        if env.exists():
            raise SystemExit(".env sudah ada; tidak ditimpa.")
        env.write_text("LABACCESS_DATABASE_URL=postgresql+psycopg://labaccess@127.0.0.1:55432/labaccess\n"
                       + "LABACCESS_SIGNING_KEY=" + secrets.token_urlsafe(48) + "\n"
                       + "LABACCESS_BIOMETRIC_KEY=" + Fernet.generate_key().decode() + "\n")
        print(".env dibuat. Kunci biometrik harus dicadangkan terpisah dari database.")
        return
    cfg = Settings()
    with Session(create_engine(cfg.database_url)) as s:
        if s.scalar(select(User).where(User.role == "admin")):
            raise SystemExit("Admin sudah ada; bootstrap ditolak. Gunakan UI atau prosedur pemulihan lokal.")
        password = secrets.token_urlsafe(18) if args.demo else getpass.getpass("Password admin (min. 12 karakter): ")
        if len(password) < 12:
            raise SystemExit("Password terlalu pendek.")
        s.add(User(nim=args.admin, name="Pengelola pilot", role="admin", password_hash=hasher.hash(password)))
        credentials = {"admin": {"nim": args.admin, "password": password}}
        if args.demo:
            for nim, name in [("DEMO001", "Mahasiswa Sintetis Satu"), ("DEMO002", "Mahasiswa Sintetis Dua")]:
                secret = secrets.token_urlsafe(16)
                s.add(User(nim=nim, name=name, role="student", password_hash=hasher.hash(secret)))
                credentials[nim] = {"nim": nim, "password": secret}
        s.add(Audit(actor="local-bootstrap", action="admin.bootstrap", target=args.admin))
        s.commit()
        if args.demo:
            path = Path(".runtime/demo.dpapi")
            save_secret(path, credentials)
            print("Akun sintetis dibuat. Credential lokal DPAPI: .runtime/demo.dpapi; buka melalui scripts.show_demo.")
        else:
            print("Admin dibuat tanpa password bawaan.")


if __name__ == "__main__":
    main()
