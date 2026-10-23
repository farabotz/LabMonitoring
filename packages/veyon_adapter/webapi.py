"""Kontrak WebAPI v1 diperiksa pada source Veyon v4.11.4."""
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from urllib.parse import quote
import httpx
import ssl

AUTH_KEYS = "0c69b301-81b4-42d6-8fae-128cdd113314"
SCREEN_LOCK = "ccb535a2-1d24-4cc1-a709-8b47d2b2ac79"


class VeyonAdapter:
    def __init__(self, base_url: str, key_name: str, private_key: Path, ca: str = "", transport=None):
        u = urlsplit(base_url)
        if u.scheme not in ("http", "https") or (u.scheme == "http" and u.hostname not in ("127.0.0.1", "::1", "localhost")):
            raise ValueError("Veyon WebAPI harus TLS atau loopback tepercaya.")
        self.url, self.name, self.key, self.ca = base_url, key_name, private_key, ca
        self.transport = transport  # Injected only by contract tests.

    @contextmanager
    def connection(self, host):
        verify = ssl.create_default_context(cafile=self.ca) if self.ca else True
        with httpx.Client(base_url=self.url, verify=verify, timeout=20, transport=self.transport,
                          trust_env=False) as client:
            auth_path = "/api/v1/authentication/" + quote(host, safe="")
            r = client.post(auth_path, json={"method": AUTH_KEYS,
                            "credentials": {"keyname": self.name, "keydata": self.key.read_text()}})
            r.raise_for_status()
            connection_id = r.json()["connection-uid"]
            client.headers["Connection-Uid"] = connection_id
            try:
                yield VeyonConnection(client, host)
            finally:
                # Closing is required even after failed framebuffer/control.
                try:
                    client.delete(auth_path).raise_for_status()
                except httpx.HTTPError:
                    pass


class VeyonConnection:
    def __init__(self, client, host):
        self.client, self.host = client, host

    def status(self):
        r = self.client.get("/api/v1/user")
        r.raise_for_status()
        return {"connected": True, "host": self.host, "windows_user": r.json(),
                "note": "Identitas Windows bersama bukan NIM LabAccess."}

    def framebuffer(self):
        r = self.client.get("/api/v1/framebuffer", params={"format": "jpeg", "quality": 70, "width": 960})
        r.raise_for_status()
        return r.content

    def screen_lock(self, active):
        r = self.client.put("/api/v1/feature/" + SCREEN_LOCK, json={"active": active, "arguments": {}})
        r.raise_for_status()
