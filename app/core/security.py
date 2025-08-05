import os
from typing import Optional

from cryptography.fernet import Fernet

FERNET_KEY = os.environ.get("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY is not set in environment")

fernet = Fernet(FERNET_KEY.encode())


def encrypt(data: Optional[str]) -> Optional[str]:
    if not data:
        return None
    return fernet.encrypt(data.encode()).decode()


def decrypt(data: Optional[str]) -> Optional[str]:
    if not data:
        return None
    return fernet.decrypt(data.encode()).decode()
