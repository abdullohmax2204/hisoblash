"""Account model."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    """Financial account (card, cash, savings, etc.).

    balance is a cached value updated transactionally alongside
    every transaction insert/update/delete. It can be recalculated
    from transactions as a verification mechanism.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(10), default="💳", nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), default=Decimal("0"), nullable=False
    )
    is_savings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account",
                                foreign_keys="Transaction.account_id", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r} balance={self.balance}>"
