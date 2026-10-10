"""Transaction model — the source of truth for all financial operations."""

import enum
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class TransactionType(str, enum.Enum):
    """All possible financial operation types."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    SAVING = "SAVING"
    SAVING_WITHDRAW = "SAVING_WITHDRAW"
    DEBT_GIVEN = "DEBT_GIVEN"
    DEBT_RETURN = "DEBT_RETURN"


class Transaction(Base, TimestampMixin):
    """A single financial operation.

    This is the source of truth for all money movement.

    Fields:
        account_id: The primary account affected (source for expenses,
                    destination for income).
        related_account_id: The secondary account for transfers/savings
                           (destination for transfers, savings account for savings).
        debt_id: Link to a Debt record for debt-related transactions.
        description: Optional note about the transaction.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), default="UZS", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=4), default=Decimal("1.0"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(30), default="manual_web", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    related_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    debt_id: Mapped[int | None] = mapped_column(
        ForeignKey("debts.id"), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship(
        "Account", back_populates="transactions", foreign_keys=[account_id]
    )
    related_account = relationship("Account", foreign_keys=[related_account_id])
    category = relationship("Category", back_populates="transactions")
    debt = relationship("Debt", back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.type} "
            f"amount={self.amount} account_id={self.account_id}>"
        )
