# backend/app/crypto.py

from cryptography.fernet import Fernet
from app.config import get_settings


def _get_fernet() -> Fernet:
    key = get_settings().portal_password_key
    return Fernet(key.encode())


def encrypt_portal_password(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_portal_password(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
