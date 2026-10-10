"""Currency and exchange rate service.

Handles Central Bank of Uzbekistan (CBU) rates, conversions, and multi-currency projections.
"""

from decimal import Decimal, ROUND_HALF_EVEN
import logging
import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)

# Default baseline fallback rates if network/CBU is unreachable
DEFAULT_RATES = {
    "USD": Decimal("12850.00"),
    "EUR": Decimal("13950.00"),
    "RUB": Decimal("138.00"),
}


class CurrencyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_rates(self) -> dict[str, dict]:
        """Fetch all stored rates from DB, with fallback defaults for missing currencies."""
        query = select(ExchangeRate)
        res = await self.session.execute(query)
        db_rates = {r.currency: {"rate": r.rate_to_uzs, "diff": r.diff, "updated_at": r.updated_at} for r in res.scalars().all()}

        result = {}
        for cur in ["USD", "EUR", "RUB"]:
            if cur in db_rates:
                result[cur] = db_rates[cur]
            else:
                result[cur] = {
                    "rate": DEFAULT_RATES.get(cur, Decimal("1.0")),
                    "diff": Decimal("0.0"),
                    "updated_at": None,
                }
        return result

    async def get_rate(self, currency: str) -> Decimal:
        """Get exchange rate for a single currency relative to UZS (e.g. 1 USD = X UZS)."""
        cur = currency.upper().strip()
        if cur == "UZS":
            return Decimal("1.0")

        query = select(ExchangeRate).where(ExchangeRate.currency == cur)
        res = await self.session.execute(query)
        record = res.scalar_one_or_none()
        if record:
            return record.rate_to_uzs

        return DEFAULT_RATES.get(cur, Decimal("1.0"))

    async def update_rate(self, currency: str, rate_to_uzs: Decimal, diff: Decimal | None = None) -> ExchangeRate:
        """Set or update an exchange rate in the database."""
        cur = currency.upper().strip()
        query = select(ExchangeRate).where(ExchangeRate.currency == cur)
        res = await self.session.execute(query)
        record = res.scalar_one_or_none()

        if record:
            record.rate_to_uzs = rate_to_uzs
            if diff is not None:
                record.diff = diff
        else:
            record = ExchangeRate(currency=cur, rate_to_uzs=rate_to_uzs, diff=diff or Decimal("0"))
            self.session.add(record)

        await self.session.flush()
        return record

    async def fetch_cbu_rates(self) -> bool:
        """Fetch official daily exchange rates from Central Bank of Uzbekistan (CBU) API."""
        url = "https://cbu.uz/ru/arkhiv-kursov-valyut/json/"
        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        logger.warning("CBU API returned HTTP %d", resp.status)
                        return False
                    data = await resp.json()

            for item in data:
                code = item.get("Ccy")
                if code in ("USD", "EUR", "RUB"):
                    rate_val = Decimal(str(item.get("Rate", "0")))
                    diff_val = Decimal(str(item.get("Diff", "0")))
                    if rate_val > Decimal("0"):
                        await self.update_rate(code, rate_val, diff_val)

            logger.info("Successfully synchronized exchange rates with CBU API")
            return True
        except Exception as e:
            logger.warning("Failed to fetch CBU exchange rates: %s", e)
            return False

    @staticmethod
    def convert(amount: Decimal, from_cur: str, to_cur: str, rates: dict[str, Decimal]) -> Decimal:
        """Convert amount between currencies using rate relative to UZS."""
        from_c = from_cur.upper().strip()
        to_c = to_cur.upper().strip()

        if from_c == to_c:
            return amount

        # Convert from source to UZS
        rate_from = rates.get(from_c, Decimal("1.0")) if from_c != "UZS" else Decimal("1.0")
        in_uzs = amount * rate_from

        # Convert from UZS to target
        rate_to = rates.get(to_c, Decimal("1.0")) if to_c != "UZS" else Decimal("1.0")
        if rate_to <= Decimal("0"):
            return in_uzs

        converted = (in_uzs / rate_to).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        return converted
