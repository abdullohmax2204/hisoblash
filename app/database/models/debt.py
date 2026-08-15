"""Debt model."""

import enum
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class DebtType(str, enum.Enum):
    """Direction of the debt."""

    GIVEN = "GIVEN"   # I gave money (they owe me)
    TAKEN = "TAKEN"   # I took money (I owe them)


class Debt(Base, TimestampMixin):
    """A debt record tracking money owed.

    original_amount: The initial debt amount.
    remaining_amount: How much is still owed (decreases with returns).
    is_settled: True when remaining_amount reaches 0.
    """

    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # GIVEN or TAKEN
    original_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    remaining_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="debts")
    transactions = relationship("Transaction", back_populates="debt", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<Debt id={self.id} person={self.person_name!r} "
            f"type={self.type} remaining={self.remaining_amount}>"
        )
