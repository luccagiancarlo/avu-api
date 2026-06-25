"""Conversão de .p12 (PKCS12) para SSLContext usado pelo httpx.

O legado Java usa `KeyStore.getInstance("PKCS12")` com `.load(fis, password)`.
Em Python fazemos o equivalente com `cryptography.hazmat.primitives.serialization.pkcs12`,
materializando cert + key como arquivos PEM temporários no FS do container
para que o `ssl.SSLContext.load_cert_chain` consiga lê-los.
"""

from __future__ import annotations

import ssl
import tempfile
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


def _p12_to_pem(p12_path: Path, p12_password: str) -> tuple[Path, Path]:
    p12_bytes = p12_path.read_bytes()
    key, cert, _additional = pkcs12.load_key_and_certificates(p12_bytes, p12_password.encode())
    if key is None or cert is None:
        raise RuntimeError(f"P12 inválido: {p12_path}")

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_file = Path(tempfile.mkstemp(suffix=".crt")[1])
    key_file = Path(tempfile.mkstemp(suffix=".key")[1])
    cert_file.write_bytes(cert_pem)
    key_file.write_bytes(key_pem)
    key_file.chmod(0o600)
    return cert_file, key_file


@lru_cache(maxsize=4)
def build_ssl_context(p12_path: str, p12_password: str) -> ssl.SSLContext:
    """Cria SSLContext com mTLS. Cacheado por (p12_path, p12_password)."""
    cert_file, key_file = _p12_to_pem(Path(p12_path), p12_password)
    ctx = ssl.create_default_context()
    # ⚠️ Em produção mantemos verify=True. O Java legado desligava verificação;
    # aqui vamos confiar no truststore padrão do sistema (Mozilla CA bundle).
    ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return ctx
