"""Debt service — manages giving, taking, and returning debts."""

from decimal import Decimal
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.debt import Debt, DebtType
from app.database.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


class DebtService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def give_debt(
        self,
        user_id: int,
        person_name: str,
        amount: Decimal,
        account_id: int,
    ) -> tuple[Debt, Transaction, Account]:
        """Give debt (I lent money to someone):
        - Deduct from account
        - Create Debt record (GIVEN)
        - Create DEBT_GIVEN transaction
        - Total capital remains unchanged (cash becomes receivable asset)
        """
        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")

        account = await self.session.get(Account, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Счет не найден")

        if account.balance < amount:
            raise ValueError(f"Недостаточно средств на счете {account.name}")

        account.balance -= amount

        clean_person = person_name[:40].strip()
        if not clean_person:
            raise ValueError("Имя человека не может быть пустым")

        debt = Debt(
            user_id=user_id,
            person_name=clean_person,
            type=DebtType.GIVEN.value,
            original_amount=amount,
            remaining_amount=amount,
            is_settled=False,
        )
        self.session.add(debt)
        await self.session.flush()

        tx = Transaction(
            user_id=user_id,
            account_id=account.id,
            debt_id=debt.id,
            type=TransactionType.DEBT_GIVEN.value,
            amount=amount,
            description=f"Дал в долг: {clean_person}",
        )
        self.session.add(tx)
        await self.session.flush()

        return debt, tx, account

    async def take_debt(
        self,
        user_id: int,
        person_name: str,
        amount: Decimal,
        account_id: int,
    ) -> tuple[Debt, Transaction, Account]:
        """Take debt (I borrowed money from someone):
        - Add to account
        - Create Debt record (TAKEN)
        - Create DEBT_TAKEN / INCOME transaction
        """
        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")

        account = await self.session.get(Account, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Счет не найден")

        account.balance += amount

        clean_person = person_name[:40].strip()
        if not clean_person:
            raise ValueError("Имя человека не может быть пустым")

        debt = Debt(
            user_id=user_id,
            person_name=clean_person,
            type=DebtType.TAKEN.value,
            original_amount=amount,
            remaining_amount=amount,
            is_settled=False,
        )
        self.session.add(debt)
        await self.session.flush()

        tx = Transaction(
            user_id=user_id,
            account_id=account.id,
            debt_id=debt.id,
            type=TransactionType.INCOME.value,
            amount=amount,
            description=f"Взял в долг у: {person_name}",
        )
        self.session.add(tx)
        await self.session.flush()

        return debt, tx, account

    async def return_debt(
        self,
        user_id: int,
        debt_id: int,
        amount: Decimal,
        account_id: int,
    ) -> tuple[Debt, Transaction, Account]:
        """Return / settle a debt (someone returned money to user, or user paid back):
        If debt.type == GIVEN (someone returning to me):
          - Add to account
          - Decrease debt remaining amount
          - If remaining == 0 -> is_settled = True
        """
        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")

        debt = await self.session.get(Debt, debt_id)
        if not debt or debt.user_id != user_id:
            raise ValueError("Запись о долге не найдена")

        if amount > debt.remaining_amount:
            raise ValueError(f"Сумма возврата превышает остаток долга ({debt.remaining_amount:,.0f} сум)".replace(",", " "))

        account = await self.session.get(Account, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Счет не найден")

        if debt.type == DebtType.GIVEN.value:
            # Money returned to me -> account balance increases
            account.balance += amount
            debt.remaining_amount -= amount
            if debt.remaining_amount == Decimal("0"):
                debt.is_settled = True

            tx = Transaction(
                user_id=user_id,
                account_id=account.id,
                debt_id=debt.id,
                type=TransactionType.DEBT_RETURN.value,
                amount=amount,
                description=f"Возврат долга от: {debt.person_name}",
            )
            self.session.add(tx)

        else:
            # I am returning debt to someone -> my account balance decreases
            if account.balance < amount:
                raise ValueError(f"Недостаточно средств на счете {account.name}")

            account.balance -= amount
            debt.remaining_amount -= amount
            if debt.remaining_amount == Decimal("0"):
                debt.is_settled = True

            tx = Transaction(
                user_id=user_id,
                account_id=account.id,
                debt_id=debt.id,
                type=TransactionType.EXPENSE.value,
                amount=amount,
                description=f"Погашение моего долга перед: {debt.person_name}",
            )
            self.session.add(tx)

        await self.session.flush()
        return debt, tx, account

    async def get_active_debts(self, user_id: int, debt_type: str = DebtType.GIVEN.value) -> list[Debt]:
        """Get all unsettled debts for user."""
        query = (
            select(Debt)
            .where(Debt.user_id == user_id, Debt.type == debt_type, Debt.is_settled == False)
            .order_by(Debt.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_debt_by_id(self, debt_id: int, user_id: int) -> Debt | None:
        query = select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
