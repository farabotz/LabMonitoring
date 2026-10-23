"""CA/cert pilot lokal, bukan sertifikat publik. Private key tidak keluar direktori target."""
import argparse
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate(root, hostname, ip="127.0.0.1"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    paths = [root / name for name in ["ca.pem", "ca.key", "server.pem", "server.key"]]
    if any(p.exists() for p in paths):
        raise ValueError("Berkas TLS sudah ada; tidak ditimpa.")
    t = datetime.now(timezone.utc)
    ca_key, key = rsa.generate_private_key(public_exponent=65537, key_size=3072), rsa.generate_private_key(public_exponent=65537, key_size=3072)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LabAccess Pilot CA")])
    ca = x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(t - timedelta(minutes=5)).not_valid_after(t + timedelta(days=90)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True).sign(ca_key, hashes.SHA256())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    cert = x509.CertificateBuilder().subject_name(name).issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(t - timedelta(minutes=5)).not_valid_after(t + timedelta(days=30)).add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True).add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname), x509.IPAddress(ip_address(ip))]), critical=False).add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False).sign(ca_key, hashes.SHA256())
    for path, obj in [(paths[0], ca), (paths[2], cert)]:
        path.write_bytes(obj.public_bytes(serialization.Encoding.PEM))
    for path, obj in [(paths[1], ca_key), (paths[3], key)]:
        path.write_bytes(obj.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return paths


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hostname", required=True)
    p.add_argument("--ip", default="127.0.0.1")
    p.add_argument("--out", type=Path, default=Path(".runtime/tls"))
    args = p.parse_args()
    generate(args.out, args.hostname, args.ip)
    print("CA pilot 90 hari dan server cert 30 hari dibuat. Batasi ACL private key; distribusikan hanya ca.pem ke klien.")


if __name__ == "__main__":
    main()
