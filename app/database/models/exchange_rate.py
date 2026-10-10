"""ExchangeRate model — tracks official and market exchange rates to base currency UZS."""

from decimal import Decimal
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base, TimestampMixin


class ExchangeRate(Base, TimestampMixin):
    """Stores exchange rates relative to the base currency (UZS).

    E.g.: currency="USD", rate_to_uzs=12850.00
    """

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    rate_to_uzs: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=4), nullable=False
    )
    diff: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=15, scale=4), nullable=True, default=Decimal("0")
    )

    def __repr__(self) -> str:
        return f"<ExchangeRate 1 {self.currency} = {self.rate_to_uzs} UZS>"
