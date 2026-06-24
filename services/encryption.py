"""
Enkripsi NIK menggunakan AES-CBC.
Key diambil dari environment variable NIK_ENCRYPTION_KEY.
"""
import os
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

NIK_KEY = os.getenv('NIK_ENCRYPTION_KEY', '')

# AES block size = 16 bytes
BLOCK_SIZE = 16


def _derive_key(passphrase: str) -> bytes:
    """Derive 32-byte key dari passphrase menggunakan SHA-256."""
    return hashlib.sha256(passphrase.encode('utf-8')).digest()


def _pad(data: bytes) -> bytes:
    """PKCS7 padding."""
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)


def _unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    pad_len = data[-1]
    return data[:-pad_len]


def encrypt_nik(plaintext: str) -> str:
    """
    Encrypt NIK string menggunakan AES-CBC.
    Returns: base64 encoded string (IV + ciphertext).
    """
    if not NIK_KEY:
        raise ValueError("NIK_ENCRYPTION_KEY belum diset di .env")

    if not plaintext:
        return ''

    from Crypto.Cipher import AES

    key = _derive_key(NIK_KEY)
    iv = os.urandom(BLOCK_SIZE)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = _pad(plaintext.encode('utf-8'))
    ciphertext = cipher.encrypt(padded)

    # gabungkan IV + ciphertext, lalu base64 encode
    return base64.b64encode(iv + ciphertext).decode('utf-8')


def decrypt_nik(ciphertext: str) -> str:
    """
    Decrypt NIK string dari AES-CBC encrypted base64.
    """
    if not NIK_KEY:
        raise ValueError("NIK_ENCRYPTION_KEY belum diset di .env")

    if not ciphertext:
        return ''

    from Crypto.Cipher import AES

    raw = base64.b64decode(ciphertext)
    iv = raw[:BLOCK_SIZE]
    enc = raw[BLOCK_SIZE:]

    key = _derive_key(NIK_KEY)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(enc)

    return _unpad(decrypted).decode('utf-8')
