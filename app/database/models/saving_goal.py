"""SavingGoal model — goals and targets for savings."""

from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class SavingGoal(Base, TimestampMixin):
    """Target/goal for savings (e.g. 'Ноутбук', 'Машина', 'Подушка безопасности')."""

    __tablename__ = "saving_goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", backref="saving_goals")

    def __repr__(self) -> str:
        return f"<SavingGoal id={self.id} name={self.name!r} target={self.target_amount}>"
