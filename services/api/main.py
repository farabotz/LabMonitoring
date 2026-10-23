import csv
import hmac
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .models import Audit, Challenge, Device, Enrollment, LabSession, RateBucket, User, now
from .schemas import (Credentials, DeviceEnroll, DeviceUpdate, EnrollmentCreate, FaceChallenge,
                      Heartbeat, PasswordLogin, PasswordReset, Reason, UserCreate, UserState)
from .security import decode, digest, hasher, keyed_digest, token, verify_password


def iso(t):
    return t.isoformat(timespec="milliseconds") + "Z" if t else None


def safe_csv(value):
    value = str(value or "")
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value


def create_app(settings: Settings | None = None):
    cfg = settings or Settings()
    cipher = Fernet(cfg.biometric_key.get_secret_value())
    engine = create_engine(cfg.database_url, pool_pre_ping=True,
                           **({"connect_args": {"check_same_thread": False}} if cfg.database_url.startswith("sqlite") else {}))
    factory = sessionmaker(engine, expire_on_commit=False)
    # Rate counters need an independent pool: request authentication already holds
    # a DB connection. Sharing a bounded pool would deadlock at >= pool capacity.
    rate_engine = create_engine(cfg.database_url, pool_pre_ping=True,
                               **({"connect_args": {"check_same_thread": False}} if cfg.database_url.startswith("sqlite") else {"pool_size": 5, "max_overflow": 5}))
    rate_factory = sessionmaker(rate_engine)
    @asynccontextmanager
    async def lifespan(_):
        with factory.begin() as startup_db:
            startup_db.add(Audit(actor="server", action="config.loaded", target="api", detail=json.dumps({
                "heartbeat_s": cfg.heartbeat_seconds, "stale_s": cfg.stale_seconds,
                "grace_minutes": cfg.grace_minutes, "retention_days": cfg.retention_days,
                "face_experimental": cfg.face_enabled, "face_threshold": cfg.face_threshold,
                "veyon_key_configured": bool(cfg.veyon_private_key_path)}, separators=(",", ":"))))
        yield
        engine.dispose()
        rate_engine.dispose()
    app = FastAPI(title=cfg.app_name, version="0.1.0", lifespan=lifespan)
    from .body_limit import BodyLimitMiddleware
    app.add_middleware(BodyLimitMiddleware)
    app.state.engine, app.state.factory, app.state.settings = engine, factory, cfg

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        from starlette.responses import JSONResponse
        local = request.client and request.client.host in ("127.0.0.1", "::1", "testclient")
        if request.url.scheme != "https" and not (cfg.allow_loopback_http and local):
            return JSONResponse({"detail": "TLS wajib untuk akses jaringan."}, status_code=426)
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Content-Length tidak valid."}, status_code=400)
        if length > 6_000_000:
            return JSONResponse({"detail": "Sampel terlalu besar."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def db():
        with factory() as s:
            try:
                yield s
            finally:
                s.rollback()

    def audit(s, actor, action, target="", detail=""):
        s.add(Audit(actor=actor, action=action, target=target, detail=detail))

    def rate(label, maximum=5):
        # Atomic fixed window, shared by API processes, survives restarts.
        t = now()
        minute = t.replace(second=0, microsecond=0)
        key = keyed_digest(cfg.signing_key.get_secret_value(), label + minute.isoformat())
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sq_insert
        insert = sq_insert if engine.dialect.name == "sqlite" else pg_insert
        with rate_factory.begin() as rs:
            stmt = insert(RateBucket).values(key=key, count=1, until=minute + timedelta(minutes=1))
            count = rs.scalar(stmt.on_conflict_do_update(index_elements=[RateBucket.key],
                             set_={"count": RateBucket.count + 1}).returning(RateBucket.count))
        if count > maximum:
            raise HTTPException(429, "Terlalu banyak percobaan. Tunggu satu menit.", headers={"Retry-After": "60"})

    def device(s: Session = Depends(db), x_device_id: str = Header(default=""),
               x_device_secret: str = Header(default="")):
        d = s.get(Device, x_device_id)
        if not d or not d.active or not hmac.compare_digest(d.secret_hash, digest(x_device_secret)):
            raise HTTPException(401, "Perangkat tidak sah/nonaktif. Hubungi pengelola.")
        return d

    def claims(authorization: str = Header(default="")):
        try:
            if not authorization.startswith("Bearer "):
                raise ValueError()
            return decode(cfg, authorization[7:])
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "Token tidak sah atau kedaluwarsa.")

    def staff(c=Depends(claims), s: Session = Depends(db)):
        u = s.get(User, c["sub"])
        if c["kind"] != "admin" or not u or not u.active or u.role not in ("admin", "operator") or c.get("ver") != u.auth_version:
            raise HTTPException(403, "Hak operator/admin diperlukan.")
        return u

    def admin(u: User = Depends(staff)):
        if u.role != "admin":
            raise HTTPException(403, "Hak admin diperlukan.")
        return u

    def own_session(c=Depends(claims), d: Device = Depends(device), s: Session = Depends(db)):
        row = s.get(LabSession, c["sub"])
        if c["kind"] != "session" or c.get("device") != d.id or not row or row.device_id != d.id:
            raise HTTPException(403, "Sesi tidak aktif atau bukan milik perangkat ini.")
        return row

    def session_data(s, row, include_token=False):
        u = s.get(User, row.user_id)
        data = {"id": row.id, "device_id": row.device_id, "nim": u.nim, "name": u.name,
                "method": row.method, "started_at": iso(row.started_at), "last_seen": iso(row.last_seen),
                "ended_at": iso(row.ended_at), "end_reason": row.end_reason, "status": row.status,
                "duration_seconds": max(0, int(((row.ended_at or now()) - row.started_at).total_seconds())),
                "connection": "stale" if now() - row.last_seen > timedelta(seconds=cfg.stale_seconds) else "online"}
        if include_token:
            data["token"] = token(cfg, row.id, "session", device=row.device_id)
        return data

    def open_session(s, d, u, method, key, proof):
        # Device row locks serialize attempts on a PC; partial unique indexes arbitrate across PCs/NIMs.
        s.scalar(select(Device).where(Device.id == d.id).with_for_update())
        fingerprint = keyed_digest(cfg.signing_key.get_secret_value(), json.dumps([d.id, u.id, method, proof]))
        old = s.scalar(select(LabSession).where(LabSession.request_key == key))
        if old:
            if old.request_digest != fingerprint or old.ended_at:
                raise HTTPException(409, "Idempotency key sudah dipakai untuk permintaan lain/selesai.")
            return session_data(s, old, True)
        row = LabSession(user_id=u.id, device_id=d.id, method=method, request_key=key, request_digest=fingerprint)
        d.last_seen = now()
        s.add(row)
        audit(s, u.nim, "session.open", d.id, method)
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            old = s.scalar(select(LabSession).where(LabSession.request_key == key))
            if old and old.request_digest == fingerprint and not old.ended_at:
                return session_data(s, old, True)
            raise HTTPException(409, "NIM atau PC sudah memiliki sesi aktif. Minta admin menyelesaikan sesi lama.")
        return session_data(s, row, True)

    @app.get("/health")
    def health(s: Session = Depends(db)):
        s.execute(select(1))
        return {"status": "ok", "name": cfg.app_name, "server_time": iso(now()),
                "heartbeat_seconds": cfg.heartbeat_seconds, "stale_seconds": cfg.stale_seconds,
                "grace_minutes": cfg.grace_minutes, "face_experimental": cfg.face_enabled,
                "os_enforcement": "belum_diverifikasi"}

    @app.post("/auth/admin")
    def login_admin(body: Credentials, request: Request, s: Session = Depends(db)):
        rate("admin-ip:" + request.client.host, 20)
        rate("admin:" + body.nim)
        u = s.scalar(select(User).where(User.nim == body.nim))
        valid = verify_password(u.password_hash if u else None, body.password)
        if not u or not valid or not u.active or u.role not in ("admin", "operator"):
            audit(s, "anonymous", "auth.admin.failed")
            s.commit()
            raise HTTPException(401, "Akun/password tidak valid atau tidak aktif.")
        audit(s, u.nim, "auth.admin.success")
        s.commit()
        return {"token": token(cfg, u.id, "admin", ver=u.auth_version), "role": u.role, "name": u.name}

    @app.get("/admin/users")
    def users(u=Depends(staff), s: Session = Depends(db)):
        return [{"id": x.id, "nim": x.nim, "name": x.name, "role": x.role, "active": x.active,
                 "face_enrolled": bool(x.face_template)} for x in s.scalars(select(User).order_by(User.nim))]

    @app.post("/admin/users", status_code=201)
    def add_user(body: UserCreate, u=Depends(staff), s: Session = Depends(db)):
        if body.role != "student" and u.role != "admin":
            raise HTTPException(403, "Operator hanya boleh menambah mahasiswa.")
        x = User(nim=body.nim, name=body.name, password_hash=hasher.hash(body.password), role=body.role)
        s.add(x)
        audit(s, u.nim, "user.create", body.nim, body.role)
        try:
            s.commit()
        except IntegrityError:
            raise HTTPException(409, "NIM sudah terdaftar.")
        return {"id": x.id, "nim": x.nim}

    def editable_user(s, user_id, actor):
        x = s.get(User, user_id)
        if not x:
            raise HTTPException(404, "Akun tidak ditemukan.")
        if actor.role != "admin" and x.role != "student":
            raise HTTPException(403, "Operator hanya boleh mengelola mahasiswa.")
        return x

    @app.put("/admin/users/{user_id}/password")
    def reset_password(user_id: str, body: PasswordReset, u=Depends(staff), s: Session = Depends(db)):
        x = editable_user(s, user_id, u)
        x.password_hash, x.auth_version = hasher.hash(body.password), x.auth_version + 1
        audit(s, u.nim, "user.password.reset", x.nim)
        s.commit()
        return {"ok": True}

    @app.put("/admin/users/{user_id}/state")
    def state(user_id: str, body: UserState, u=Depends(staff), s: Session = Depends(db)):
        x = editable_user(s, user_id, u)
        if x.id == u.id:
            raise HTTPException(409, "Tidak boleh menonaktifkan akun sendiri.")
        x.active, x.auth_version = body.active, x.auth_version + 1
        audit(s, u.nim, "user.state", x.nim, str(body.active))
        s.commit()
        return {"ok": True}

    @app.post("/admin/enrollments")
    def enrollment(body: EnrollmentCreate, u=Depends(admin), s: Session = Depends(db)):
        value = secrets.token_urlsafe(32)
        s.add(Enrollment(digest=digest(value), expires_at=now() + timedelta(minutes=15),
                         name=body.name, veyon_host=body.veyon_host))
        audit(s, u.nim, "device.enrollment.issue", body.name)
        s.commit()
        return {"token": value, "expires_in": 900}

    @app.post("/devices/enroll", status_code=201)
    def enroll(body: DeviceEnroll, request: Request, s: Session = Depends(db)):
        rate("enroll:" + request.client.host, 10)
        e = s.scalar(select(Enrollment).where(Enrollment.digest == digest(body.token)).with_for_update())
        if not e or e.consumed_at or e.expires_at < now():
            raise HTTPException(401, "Token enrollment tidak valid, terpakai, atau kedaluwarsa.")
        secret = secrets.token_urlsafe(40)
        e.consumed_at = now()
        d = Device(id=body.device_id, name=e.name, secret_hash=digest(secret), veyon_host=e.veyon_host)
        s.add(d)
        audit(s, "enrollment", "device.register", d.id, e.name)
        try:
            s.commit()
        except IntegrityError:
            raise HTTPException(409, "ID/nama PC sudah didaftarkan. Hubungi admin.")
        return {"device_id": d.id, "device_secret": secret, "name": d.name}

    @app.post("/sessions/password")
    def password_login(body: PasswordLogin, d=Depends(device), s: Session = Depends(db)):
        # Auth is checked even on replay; password reset invalidates old login proof.
        rate("student:" + body.nim, 10)
        rate("pc:" + d.id, 20)
        u = s.scalar(select(User).where(User.nim == body.nim))
        valid = verify_password(u.password_hash if u else None, body.password)
        if not u or not valid or not u.active or u.role != "student":
            audit(s, "device:" + d.id, "auth.student.failed")
            s.commit()
            raise HTTPException(401, "NIM/password tidak valid atau akun tidak aktif.")
        return open_session(s, d, u, "password", body.request_key, body.password)

    @app.post("/devices/heartbeat")
    def heartbeat(body: Heartbeat, d=Depends(device), s: Session = Depends(db)):
        d = s.scalar(select(Device).where(Device.id == d.id).with_for_update())
        row = s.scalar(select(LabSession).where(LabSession.device_id == d.id, LabSession.ended_at.is_(None)))
        reboot = d.boot_id is not None and d.boot_id != body.boot_id
        if row and reboot:
            row.ended_at, row.status, row.end_reason = now(), "interrupted", "device_restart_detected"
            audit(s, "device:" + d.id, "session.interrupted", row.id, "last_seen adalah batas bukti penggunaan")
        elif row:
            row.last_seen = now()
        d.last_seen, d.boot_id = now(), body.boot_id
        s.commit()
        return {"server_time": iso(now()), "session": session_data(s, row, True) if row and not row.ended_at else None,
                "restart_detected": reboot, "heartbeat_seconds": cfg.heartbeat_seconds}

    @app.post("/sessions/logout")
    def logout(row=Depends(own_session), s: Session = Depends(db)):
        if row.ended_at:
            return {"ok": True}
        row.ended_at, row.status, row.end_reason = now(), "completed", "student_logout"
        audit(s, "session:" + row.id, "session.logout", row.device_id)
        s.commit()
        return {"ok": True}

    @app.get("/admin/devices")
    def devices(u=Depends(staff), s: Session = Depends(db)):
        rows = list(s.scalars(select(Device).order_by(Device.name)))
        active = {r.device_id: r for r in s.scalars(select(LabSession).where(LabSession.ended_at.is_(None)))}
        return [{"id": d.id, "name": d.name, "active": d.active, "problem": d.problem,
                 "veyon_host": d.veyon_host, "last_seen": iso(d.last_seen),
                 "online": bool(d.last_seen and now() - d.last_seen <= timedelta(seconds=cfg.stale_seconds)),
                 "session": session_data(s, active[d.id]) if d.id in active else None} for d in rows]

    @app.put("/admin/devices/{device_id}")
    def update_device(device_id: str, body: DeviceUpdate, u=Depends(admin), s: Session = Depends(db)):
        d = s.get(Device, device_id)
        if not d:
            raise HTTPException(404, "Perangkat tidak ditemukan.")
        d.problem, d.active, d.veyon_host = body.problem, body.active, body.veyon_host
        audit(s, u.nim, "device.config", d.id, "status/mapping diubah")
        s.commit()
        return {"ok": True}

    @app.post("/admin/sessions/{session_id}/end")
    def end(session_id: str, body: Reason, u=Depends(staff), s: Session = Depends(db)):
        row = s.scalar(select(LabSession).where(LabSession.id == session_id).with_for_update())
        if not row:
            raise HTTPException(404, "Sesi tidak ditemukan.")
        if not row.ended_at:
            row.ended_at, row.status, row.end_reason = now(), "interrupted", "admin: " + body.reason
            audit(s, u.nim, "session.end", row.id, body.reason)
            s.commit()
        return {"ok": True, "notice": "Pencatatan sesi diakhiri; aplikasi/pekerjaan Windows tidak ditutup."}

    def history_rows(s, nim, device_id, method, start, end, end_reason):
        q = select(LabSession).join(User)
        if nim:
            q = q.where(User.nim == nim)
        if device_id:
            q = q.where(LabSession.device_id == device_id)
        if method:
            q = q.where(LabSession.method == method)
        if end_reason:
            q = q.where(LabSession.end_reason.icontains(end_reason, autoescape=True))
        if start:
            start = start.astimezone(timezone.utc).replace(tzinfo=None) if start.tzinfo else start
            q = q.where(LabSession.started_at >= start)
        if end:
            end = end.astimezone(timezone.utc).replace(tzinfo=None) if end.tzinfo else end
            q = q.where(LabSession.started_at <= end)
        return [session_data(s, r) for r in s.scalars(q.order_by(LabSession.started_at.desc()).limit(10000))]

    @app.get("/admin/history")
    def history(nim: str = "", device_id: str = "", method: str = "", start: datetime | None = None,
                end: datetime | None = None, end_reason: str = "", u=Depends(staff), s: Session = Depends(db)):
        return history_rows(s, nim, device_id, method, start, end, end_reason)

    @app.get("/admin/history.csv")
    def export(nim: str = "", device_id: str = "", method: str = "", start: datetime | None = None,
               end: datetime | None = None, end_reason: str = "", u=Depends(staff), s: Session = Depends(db)):
        rows = history_rows(s, nim, device_id, method, start, end, end_reason)
        buf = io.StringIO()
        fields = ["id", "device_id", "nim", "name", "method", "started_at", "last_seen", "ended_at", "end_reason", "status"]
        writer = csv.writer(buf)
        writer.writerow(fields)
        writer.writerows([[safe_csv(r.get(k)) for k in fields] for r in rows])
        audit(s, u.nim, "history.export", detail=str(len(rows)))
        s.commit()
        return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="labaccess-history.csv"'})

    @app.get("/admin/audit")
    def audit_list(u=Depends(admin), s: Session = Depends(db)):
        return [{"at": iso(x.at), "actor": x.actor, "action": x.action, "target": x.target,
                 "detail": x.detail} for x in s.scalars(select(Audit).order_by(Audit.at.desc()).limit(1000))]

    def face_engine():
        if not cfg.face_enabled:
            raise HTTPException(503, "Metode wajah eksperimental belum diaktifkan; gunakan password.")
        from packages.face_verification.engine import FaceEngine
        if not hasattr(app.state, "face"):
            try:
                app.state.face = FaceEngine(Path(cfg.models_dir))
            except (ValueError, FileNotFoundError, RuntimeError):
                raise HTTPException(503, "Model wajah belum siap/terverifikasi. Gunakan password.")
        return app.state.face

    async def read_frames(files):
        if len(files) != 3:
            raise HTTPException(422, "Diperlukan tiga sampel: tengah, tantangan, tengah.")
        frames = []
        for f in files:
            raw = await f.read(1_500_001)
            await f.close()
            if len(raw) > 1_500_000:
                raise HTTPException(413, "Frame terlalu besar.")
            frames.append(raw)
        return frames

    @app.post("/face/challenges")
    def challenge(body: FaceChallenge, d=Depends(device), s: Session = Depends(db)):
        face_engine()
        rate("face-challenge:" + d.id, 10)
        c = Challenge(device_id=d.id, nim=body.nim, direction=secrets.choice(["left", "right"]),
                      expires_at=now() + timedelta(seconds=30))
        s.add(c)
        s.commit()
        return {"challenge_id": c.id, "direction": c.direction, "expires_at": iso(c.expires_at),
                "instruction": "Tengah → putar kepala sesuai arah → kembali tengah. Mitigasi replay terbatas."}

    @app.post("/sessions/face")
    async def face_login(challenge_id: str = Form(max_length=36), request_key: str = Form(min_length=16, max_length=100),
                         frames: list[UploadFile] = File(), d=Depends(device), s: Session = Depends(db)):
        engine_face = face_engine()
        rate("face:" + d.id, 10)
        c = s.scalar(select(Challenge).where(Challenge.id == challenge_id).with_for_update())
        if c and c.device_id == d.id and c.consumed:
            u = s.scalar(select(User).where(User.nim == c.nim, User.active.is_(True)))
            old = s.scalar(select(LabSession).where(LabSession.request_key == request_key))
            fingerprint = keyed_digest(cfg.signing_key.get_secret_value(), json.dumps([d.id, u.id, "face", challenge_id])) if u else ""
            if old and not old.ended_at and hmac.compare_digest(old.request_digest, fingerprint):
                return session_data(s, old, True)
        if not c or c.device_id != d.id or c.consumed or c.expires_at < now():
            raise HTTPException(401, "Tantangan tidak sah, terpakai, atau kedaluwarsa.")
        nim, direction = c.nim, c.direction
        c.consumed = True
        s.commit()  # Burn once, including failed quality/PAD/identity checks.
        raw = await read_frames(frames)
        u = s.scalar(select(User).where(User.nim == nim, User.active.is_(True), User.role == "student"))
        try:
            if not u or not u.face_template:
                raise ValueError("Wajah belum terdaftar atau akun tidak aktif. Gunakan password.")
            template = json.loads(cipher.decrypt(u.face_template))
            from starlette.concurrency import run_in_threadpool
            await run_in_threadpool(engine_face.verify, raw, template, direction, cfg.face_threshold)
        except ValueError as exc:
            audit(s, "device:" + d.id, "auth.face.failed", detail=str(exc)[:150])
            s.commit()
            raise HTTPException(401, str(exc))
        finally:
            raw.clear()
        return open_session(s, d, u, "face", request_key, challenge_id)

    @app.post("/admin/users/{user_id}/face")
    async def enroll_face(user_id: str, consent: bool = Form(), frames: list[UploadFile] = File(),
                          u=Depends(staff), s: Session = Depends(db)):
        x = editable_user(s, user_id, u)
        if x.role != "student" or not consent:
            raise HTTPException(422, "Enrollment mahasiswa memerlukan pemeriksaan identitas dan persetujuan.")
        fe = face_engine()
        raw = await read_frames(frames)
        try:
            from starlette.concurrency import run_in_threadpool
            template = await run_in_threadpool(fe.enroll, raw)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        finally:
            raw.clear()
        x.face_template, x.consent_at = cipher.encrypt(json.dumps(template).encode()), now()
        audit(s, u.nim, "face.enroll", x.nim, "consent+operator_identity_check")
        s.commit()
        return {"ok": True, "experimental": True}

    @app.delete("/admin/users/{user_id}/face")
    def delete_face(user_id: str, u=Depends(staff), s: Session = Depends(db)):
        x = editable_user(s, user_id, u)
        x.face_template, x.consent_at = None, None
        audit(s, u.nim, "face.delete", x.nim)
        s.commit()
        return {"ok": True}

    def veyon(d):
        from packages.veyon_adapter.webapi import VeyonAdapter
        if not d or not d.veyon_host:
            raise HTTPException(409, "Mapping host Veyon belum diatur admin.")
        if not cfg.veyon_private_key_path:
            raise HTTPException(503, "Kunci Veyon pada server belum dikonfigurasi.")
        return VeyonAdapter(cfg.veyon_url, cfg.veyon_key_name, Path(cfg.veyon_private_key_path), cfg.veyon_ca)

    @app.get("/admin/devices/{device_id}/veyon/status")
    def veyon_status(device_id: str, u=Depends(staff), s: Session = Depends(db)):
        d = s.get(Device, device_id)
        try:
            with veyon(d).connection(d.veyon_host) as link:
                result = link.status()
        except HTTPException:
            audit(s, u.nim, "veyon.failed", device_id, "status: configuration unavailable")
            s.commit()
            raise
        except Exception:
            audit(s, u.nim, "veyon.failed", device_id, "status")
            s.commit()
            raise HTTPException(502, "Veyon tidak terhubung. Periksa service, mapping, TLS dan kunci.")
        audit(s, u.nim, "veyon.status", device_id)
        s.commit()
        return result

    @app.get("/admin/devices/{device_id}/veyon/framebuffer")
    def framebuffer(device_id: str, u=Depends(staff), s: Session = Depends(db)):
        d = s.get(Device, device_id)
        try:
            with veyon(d).connection(d.veyon_host) as link:
                data = link.framebuffer()
        except HTTPException:
            audit(s, u.nim, "veyon.failed", device_id, "framebuffer: configuration unavailable")
            s.commit()
            raise
        except Exception:
            audit(s, u.nim, "veyon.failed", device_id, "framebuffer")
            s.commit()
            raise HTTPException(502, "Tangkapan layar Veyon tidak tersedia.")
        audit(s, u.nim, "veyon.framebuffer", device_id)
        s.commit()
        return Response(data, media_type="image/jpeg")

    @app.put("/admin/devices/{device_id}/veyon/lock")
    def veyon_lock(device_id: str, body: Reason, active: bool = True, u=Depends(admin), s: Session = Depends(db)):
        d = s.get(Device, device_id)
        try:
            with veyon(d).connection(d.veyon_host) as link:
                link.screen_lock(active)
        except HTTPException:
            audit(s, u.nim, "veyon.failed", device_id, "lock: configuration unavailable")
            s.commit()
            raise
        except Exception:
            audit(s, u.nim, "veyon.failed", device_id, "lock")
            s.commit()
            raise HTTPException(502, "Perintah Veyon gagal. Periksa keadaan PC melalui Master.")
        audit(s, u.nim, "veyon.lock" if active else "veyon.unlock", device_id, body.reason)
        s.commit()
        return {"ok": True}

    return app
