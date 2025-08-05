from datetime import datetime, timezone
from typing import Optional, cast

from sqlmodel import Field, SQLModel

from app.core.security import decrypt, encrypt


class User(SQLModel, table=True):
    telegram_id: int = Field(primary_key=True)

    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None

    email: Optional[str] = None
    token_expiry: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    @property
    def access_token(self) -> str:
        return cast(str, decrypt(self.access_token_encrypted))

    @access_token.setter
    def access_token(self, value: str):
        self.access_token_encrypted = encrypt(value) or ""

    @property
    def refresh_token(self) -> Optional[str]:
        return (
            decrypt(self.refresh_token_encrypted)
            if self.refresh_token_encrypted
            else None
        )

    @refresh_token.setter
    def refresh_token(self, value: Optional[str]):
        self.refresh_token_encrypted = encrypt(value) if value else None
