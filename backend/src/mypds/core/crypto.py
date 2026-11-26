"""Chiffrement des secrets au repos (AES-256-GCM, voir ADR-0006)."""

import os
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from mypds.core.settings import get_settings

KEY_ID = 1  # incrémenté lors d'une rotation de clé
_NONCE = 12


class SecretKeyError(RuntimeError):
    pass


def generate_key_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(fd, "wb") as f:
        f.write(secrets.token_bytes(32))


@lru_cache
def _key() -> bytes:
    path = get_settings().secret_key_file
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SecretKeyError(f"Clé de chiffrement illisible : {path}") from exc
    if len(data) != 32:
        raise SecretKeyError(f"La clé {path} doit faire exactement 32 octets")
    return data


def encrypt(plaintext: str, context: str) -> bytes:
    """Chiffre `plaintext`. `context` (ex. 'calendar_source:<id>:url') lie le secret à son propriétaire."""
    nonce = secrets.token_bytes(_NONCE)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), context.encode())
    return bytes([KEY_ID]) + nonce + ct


def decrypt(blob: bytes, context: str) -> str:
    if not blob or blob[0] != KEY_ID:
        raise SecretKeyError("Identifiant de clé inconnu")
    nonce, ct = blob[1 : 1 + _NONCE], blob[1 + _NONCE :]
    return AESGCM(_key()).decrypt(nonce, ct, context.encode()).decode()
