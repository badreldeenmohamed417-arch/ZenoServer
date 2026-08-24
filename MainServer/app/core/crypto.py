# app/core/crypto.py
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_fernet_key(secret_key: str) -> bytes:
    # نشتق مفتاح 32 بايت ثابت من الـ SECRET_KEY ونحوله لصيغة Fernet (base64)
    digest = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key(settings.SECRET_KEY))


def encrypt_secret(plain_secret: str) -> str:
    return _fernet.encrypt(plain_secret.encode()).decode()


def decrypt_secret(encrypted_secret: str) -> str:
    return _fernet.decrypt(encrypted_secret.encode()).decode()
