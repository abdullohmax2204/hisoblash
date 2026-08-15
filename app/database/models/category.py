"""Category model."""

from sqlalchemy import ForeignKey, String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """Income or expense category.

    System categories have user_id = None and are shared.
    User-created categories are linked to a specific user.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(10), default="📁", nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # INCOME or EXPENSE
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} type={self.type}>"
