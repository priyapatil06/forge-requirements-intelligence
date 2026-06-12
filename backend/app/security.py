import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import Settings


class TokenCipher:
    def __init__(self, settings: Settings):
        if settings.forge_token_encryption_key:
            key = settings.forge_token_encryption_key.encode()
        else:
            digest = hashlib.sha256(settings.forge_secret_key.encode()).digest()
            key = base64.urlsafe_b64encode(digest)
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode()).decode()
