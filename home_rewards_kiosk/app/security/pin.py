import hashlib
import os
import hmac


def hash_pin(pin: str) -> tuple[str, str]:
    salt = os.urandom(16)
    pin_hash = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 120_000)
    return salt.hex(), pin_hash.hex()


def verify_pin(pin: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    actual = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(actual, expected)
