"""Retensi eksplisit, dry-run secara default. Tidak menyentuh sesi terbuka."""
import argparse
from datetime import timedelta
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session
from services.api.config import Settings
from services.api.models import Audit, Challenge, Enrollment, LabSession, RateBucket, now


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    cfg = Settings()
    cutoff = now() - timedelta(days=cfg.retention_days)
    with Session(create_engine(cfg.database_url)) as s:
        condition = (LabSession.ended_at.is_not(None), LabSession.ended_at < cutoff)
        count = s.scalar(select(func.count()).select_from(LabSession).where(*condition))
        print(f"Sesi selesai lebih lama dari {cfg.retention_days} hari: {count}. Mode: {'apply' if args.apply else 'dry-run'}")
        if args.apply:
            s.execute(delete(LabSession).where(*condition))
            s.execute(delete(Challenge).where(Challenge.expires_at < now() - timedelta(days=1)))
            s.execute(delete(Enrollment).where(Enrollment.expires_at < now() - timedelta(days=1)))
            s.execute(delete(RateBucket).where(RateBucket.until < now() - timedelta(days=1)))
            s.add(Audit(actor="local-maintenance", action="retention.apply", target="sessions", detail=str(count)))
            s.commit()


if __name__ == "__main__":
    main()
