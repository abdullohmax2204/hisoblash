"""User model."""

from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Telegram user.

    Each user has their own accounts, categories, transactions, and debts.
    In MVP only ADMIN_USER_ID is allowed, but the schema supports multiple users.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS", nullable=False)
    monthly_salary: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=2), nullable=True
    )
    pay_cycle_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="user", lazy="selectin")
    categories = relationship("Category", back_populates="user", lazy="selectin")
    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    debts = relationship("Debt", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} name={self.name!r}>"
