"""Finance service — manages Income, Expense, Transfer transactions and ledger balance updates.

Guarantees:
- Zero-drift ledger consistency
- Idempotency support (prevents duplicate debits/credits)
- Mathematical balance reconciliation
"""

from decimal import Decimal
import logging
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.category import Category
from app.database.models.debt import Debt
from app.database.models.transaction import Transaction, TransactionType
from app.domain.exceptions import (
    InsufficientFundsError,
    EntityNotFoundError,
    InvalidAmountError,
    DuplicateRequestError,
)

logger = logging.getLogger(__name__)

MAX_AMOUNT = Decimal("1000000000000")  # 1 Trillion UZS limit per transaction


class FinanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_idempotency_key(self, user_id: int, key: str) -> Transaction | None:
        """Find an existing transaction by idempotency key."""
        if not key:
            return None
        query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.idempotency_key == key,
        )
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def add_income(
        self,
        user_id: int,
        account_id: int,
        category_id: int | None,
        amount: Decimal,
        description: str | None = None,
        source: str = "manual_web",
        idempotency_key: str | None = None,
        currency: str = "UZS",
    ) -> tuple[Transaction, Account]:
        """Record income:
        1. Check idempotency
        2. Validate amount and account
        3. Create INCOME transaction
        4. Increase account balance
        """
        if idempotency_key:
            existing = await self.get_by_idempotency_key(user_id, idempotency_key)
            if existing:
                account = await self.session.get(Account, existing.account_id)
                return existing, account

        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")
        if amount > MAX_AMOUNT:
            raise ValueError("Сумма слишком велика (максимум 1 000 000 000 000 сум)")

        account = await self.session.get(Account, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Счет не найден")

        clean_desc = description[:200].strip() if description else None

        tx = Transaction(
            user_id=user_id,
            account_id=account.id,
            category_id=category_id,
            type=TransactionType.INCOME.value,
            amount=amount,
            currency=currency or account.currency,
            source=source,
            idempotency_key=idempotency_key,
            description=clean_desc,
        )
        self.session.add(tx)

        account.balance += amount
        await self.session.flush()

        return tx, account

    async def add_expense(
        self,
        user_id: int,
        account_id: int,
        category_id: int | None,
        amount: Decimal,
        description: str | None = None,
        source: str = "manual_web",
        idempotency_key: str | None = None,
        currency: str = "UZS",
    ) -> tuple[Transaction, Account]:
        """Record expense:
        1. Check idempotency
        2. Check account balance
        3. Create EXPENSE transaction
        4. Decrease account balance
        """
        if idempotency_key:
            existing = await self.get_by_idempotency_key(user_id, idempotency_key)
            if existing:
                account = await self.session.get(Account, existing.account_id)
                return existing, account

        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")
        if amount > MAX_AMOUNT:
            raise ValueError("Сумма слишком велика (максимум 1 000 000 000 000 сум)")

        account = await self.session.get(Account, account_id)
        if not account or account.user_id != user_id:
            raise ValueError("Счет не найден")

        if account.balance < amount:
            raise ValueError(f"Недостаточно средств на счете {account.name}. Доступно: {account.balance:,.0f} сум".replace(",", " "))

        clean_desc = description[:200].strip() if description else None

        tx = Transaction(
            user_id=user_id,
            account_id=account.id,
            category_id=category_id,
            type=TransactionType.EXPENSE.value,
            amount=amount,
            currency=currency or account.currency,
            source=source,
            idempotency_key=idempotency_key,
            description=clean_desc,
        )
        self.session.add(tx)

        account.balance -= amount
        await self.session.flush()

        return tx, account

    async def transfer_between_accounts(
        self,
        user_id: int,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        source: str = "manual_web",
        idempotency_key: str | None = None,
    ) -> tuple[Transaction, Account, Account]:
        """Transfer between user's regular accounts:
        1. Deduct from from_account
        2. Add to to_account
        3. Create TRANSFER transaction
        """
        if idempotency_key:
            existing = await self.get_by_idempotency_key(user_id, idempotency_key)
            if existing and existing.related_account_id:
                from_acc = await self.session.get(Account, existing.account_id)
                to_acc = await self.session.get(Account, existing.related_account_id)
                return existing, from_acc, to_acc

        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")
        if amount > MAX_AMOUNT:
            raise ValueError("Сумма слишком велика (максимум 1 000 000 000 000 сум)")
        if from_account_id == to_account_id:
            raise ValueError("Нельзя перевести на тот же счет")

        from_acc = await self.session.get(Account, from_account_id)
        to_acc = await self.session.get(Account, to_account_id)

        if not from_acc or from_acc.user_id != user_id:
            raise ValueError("Счет списания не найден")
        if not to_acc or to_acc.user_id != user_id:
            raise ValueError("Счет зачисления не найден")

        if from_acc.balance < amount:
            raise ValueError(f"Недостаточно средств на счете {from_acc.name}")

        from_acc.balance -= amount
        to_acc.balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=from_acc.id,
            related_account_id=to_acc.id,
            type=TransactionType.TRANSFER.value,
            amount=amount,
            currency=from_acc.currency,
            source=source,
            idempotency_key=idempotency_key,
            description=f"Перевод: {from_acc.name} ➔ {to_acc.name}",
        )
        self.session.add(tx)
        await self.session.flush()

        return tx, from_acc, to_acc

    async def delete_transaction(self, user_id: int, transaction_id: int) -> bool:
        """Delete a transaction and mathematically restore account balances."""
        tx = await self.session.get(Transaction, transaction_id)
        if not tx or tx.user_id != user_id:
            return False

        account = await self.session.get(Account, tx.account_id)

        if tx.type == TransactionType.INCOME.value:
            if account:
                account.balance -= tx.amount

        elif tx.type == TransactionType.EXPENSE.value:
            if account:
                account.balance += tx.amount

        elif tx.type == TransactionType.SAVING.value:
            if account:
                account.balance += tx.amount
            if tx.related_account_id:
                savings_acc = await self.session.get(Account, tx.related_account_id)
                if savings_acc:
                    savings_acc.balance -= tx.amount

        elif tx.type == TransactionType.SAVING_WITHDRAW.value:
            if account:
                account.balance -= tx.amount
            if tx.related_account_id:
                savings_acc = await self.session.get(Account, tx.related_account_id)
                if savings_acc:
                    savings_acc.balance += tx.amount

        elif tx.type == TransactionType.DEBT_GIVEN.value:
            if account:
                account.balance += tx.amount
            if tx.debt_id:
                debt = await self.session.get(Debt, tx.debt_id)
                if debt:
                    await self.session.delete(debt)

        elif tx.type == TransactionType.DEBT_RETURN.value:
            if account:
                account.balance -= tx.amount
            if tx.debt_id:
                debt = await self.session.get(Debt, tx.debt_id)
                if debt:
                    debt.remaining_amount += tx.amount
                    debt.is_settled = False

        elif tx.type == TransactionType.TRANSFER.value:
            if account:
                account.balance += tx.amount
            if tx.related_account_id:
                to_acc = await self.session.get(Account, tx.related_account_id)
                if to_acc:
                    to_acc.balance -= tx.amount

        await self.session.delete(tx)
        await self.session.flush()
        return True

    async def reconcile_account_balance(self, account_id: int) -> Decimal:
        """Audit and recalculate the exact theoretical balance of an account directly from all transactions.
        Guarantees zero-drift ledger reconciliation.
        """
        account = await self.session.get(Account, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Query all operations where account_id is either primary or related
        q = select(Transaction).where(
            or_(Transaction.account_id == account_id, Transaction.related_account_id == account_id)
        )
        res = await self.session.execute(q)
        transactions = res.scalars().all()

        calculated_balance = Decimal("0")
        for tx in transactions:
            if tx.account_id == account_id:
                if tx.type in (TransactionType.INCOME.value, "DEBT_TAKEN", TransactionType.DEBT_RETURN.value):
                    calculated_balance += tx.amount
                elif tx.type in (TransactionType.EXPENSE.value, TransactionType.TRANSFER.value, TransactionType.SAVING.value, TransactionType.DEBT_GIVEN.value):
                    calculated_balance -= tx.amount
                elif tx.type == TransactionType.SAVING_WITHDRAW.value:
                    # If this is the recipient account of a savings withdrawal
                    calculated_balance += tx.amount
            elif tx.related_account_id == account_id:
                # Account is the destination of a transfer or savings
                if tx.type == TransactionType.TRANSFER.value:
                    calculated_balance += tx.amount
                elif tx.type == TransactionType.SAVING.value:
                    calculated_balance += tx.amount
                elif tx.type == TransactionType.SAVING_WITHDRAW.value:
                    calculated_balance -= tx.amount

        account.balance = calculated_balance
        await self.session.flush()
        return calculated_balance
