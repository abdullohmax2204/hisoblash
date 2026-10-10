"""Authorized secondary Telegram users model."""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, TimestampMixin


class AuthorizedTelegramUser(Base, TimestampMixin):
    """Stores secondary Telegram IDs authorized via emergency password.

    All authorized accounts operate on the single master personal finance profile.
    """

    __tablename__ = "authorized_telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    def __repr__(self) -> str:
        return f"<AuthorizedTelegramUser id={self.id} telegram_id={self.telegram_id} name={self.name!r}>"
