"""Account service — manages bank accounts, balances, and capital overview."""

from decimal import Decimal
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.debt import Debt, DebtType
from app.database.models.transaction import Transaction, TransactionType
from app.database.models.user import User

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_accounts(self, user_id: int, include_savings: bool = True) -> list[Account]:
        """Get all active accounts for user, auto-seeding defaults if empty."""
        query = select(Account).where(Account.user_id == user_id, Account.is_active == True)
        if not include_savings:
            query = query.where(Account.is_savings == False)
        query = query.order_by(Account.sort_order, Account.id)
        result = await self.session.execute(query)
        accounts = list(result.scalars().all())

        if not accounts and user_id:
            from app.services.user_service import DEFAULT_ACCOUNTS
            for acc_data in DEFAULT_ACCOUNTS:
                account = Account(
                    user_id=user_id,
                    balance=Decimal("0"),
                    **acc_data,
                )
                self.session.add(account)
            await self.session.flush()
            # Re-fetch
            result = await self.session.execute(query)
            accounts = list(result.scalars().all())

        return accounts

    async def get_account_by_id(self, account_id: int, user_id: int) -> Account | None:
        """Get account by ID ensuring it belongs to user."""
        query = select(Account).where(Account.id == account_id, Account.user_id == user_id, Account.is_active == True)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_savings_account(self, user_id: int) -> Account:
        """Get or create savings account for user."""
        query = select(Account).where(Account.user_id == user_id, Account.is_savings == True)
        result = await self.session.execute(query)
        acc = result.scalar_one_or_none()
        if not acc:
            acc = Account(
                user_id=user_id,
                name="Накопления",
                icon="💵",
                balance=Decimal("0"),
                is_savings=True,
                sort_order=99,
            )
            self.session.add(acc)
            await self.session.flush()
        return acc

    async def create_account(self, user_id: int, name: str, icon: str = "💳", initial_balance: Decimal = Decimal("0")) -> Account:
        """Create new regular account."""
        clean_name = name[:40].strip()
        if not clean_name:
            raise ValueError("Название счёта не может быть пустым")

        account = Account(
            user_id=user_id,
            name=clean_name,
            icon=icon,
            balance=initial_balance,
            is_savings=False,
        )
        self.session.add(account)
        await self.session.flush()

        if initial_balance > Decimal("0"):
            # Record initial balance transaction
            tx = Transaction(
                user_id=user_id,
                account_id=account.id,
                type=TransactionType.INCOME.value,
                amount=initial_balance,
                description="Начальный баланс",
            )
            self.session.add(tx)
            await self.session.flush()

        return account

    async def get_bank_summary(self, user_id: int) -> dict:
        """Calculate bank overview:
        - List of regular accounts with balances
        - Total available funds (sum of regular accounts)
        - Savings balance
        - Debts given (money owed to user)
        - Debts taken (money user owes)
        - Total capital = available + savings + debts_given - debts_taken
        """
        regular_accounts = await self.get_user_accounts(user_id, include_savings=False)
        savings_account = await self.get_savings_account(user_id)

        available_funds = sum((acc.balance for acc in regular_accounts), Decimal("0"))
        savings_balance = savings_account.balance

        # Debts owed to user (GIVEN)
        q_debts_given = select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(
            Debt.user_id == user_id,
            Debt.type == DebtType.GIVEN.value,
            Debt.is_settled == False,
        )
        res_given = await self.session.execute(q_debts_given)
        debts_given = Decimal(str(res_given.scalar() or 0))

        # Debts user owes (TAKEN)
        q_debts_taken = select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(
            Debt.user_id == user_id,
            Debt.type == DebtType.TAKEN.value,
            Debt.is_settled == False,
        )
        res_taken = await self.session.execute(q_debts_taken)
        debts_taken = Decimal(str(res_taken.scalar() or 0))

        total_capital = available_funds + savings_balance + debts_given - debts_taken

        return {
            "regular_accounts": regular_accounts,
            "savings_account": savings_account,
            "available_funds": available_funds,
            "savings_balance": savings_balance,
            "debts_given": debts_given,
            "debts_taken": debts_taken,
            "total_capital": total_capital,
        }
