"""Domain command and data contracts (Pydantic V2) for Hisoblash Core.

Delivery mechanisms (REST API, Bot Handlers) validate input into these DTOs
before dispatching to Domain Services.
"""

from datetime import date, datetime
from decimal import Decimal
import enum
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    SAVING = "SAVING"
    SAVING_WITHDRAW = "SAVING_WITHDRAW"
    DEBT_GIVEN = "DEBT_GIVEN"
    DEBT_TAKEN = "DEBT_TAKEN"
    DEBT_RETURN = "DEBT_RETURN"


class DebtType(str, enum.Enum):
    GIVEN = "GIVEN"  # Мне должны (Active asset)
    TAKEN = "TAKEN"  # Я должен (Liability)


class TransactionSource(str, enum.Enum):
    MANUAL_WEB = "manual_web"
    BOT_TEXT = "bot_text"
    BOT_VOICE = "bot_voice"
    BOT_KEYBOARD = "bot_keyboard"
    SYSTEM = "system"


MAX_FINANCIAL_AMOUNT = Decimal("1000000000000")  # 1 Trillion limit


# -----------------------------------------------------------------------------
# COMMAND CONTRACTS (Inputs to Core)
# -----------------------------------------------------------------------------

class CreateTransactionCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    account_id: int
    type: TransactionType
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    currency: str = Field(default="UZS", max_length=10)
    exchange_rate: Decimal = Field(default=Decimal("1.0"), gt=0)
    category_id: int | None = None
    related_account_id: int | None = None
    debt_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class CreateIncomeCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class CreateExpenseCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class TransferCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    from_account_id: int
    to_account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    description: str | None = Field(default=None, max_length=500)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)

    @field_validator("to_account_id")
    @classmethod
    def accounts_must_differ(cls, v: int, info):
        from_id = info.data.get("from_account_id")
        if from_id is not None and v == from_id:
            raise ValueError("Счет списания и счет зачисления не могут совпадать")
        return v


class GiveDebtCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    account_id: int
    person_name: str = Field(min_length=1, max_length=100)
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class TakeDebtCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    account_id: int
    person_name: str = Field(min_length=1, max_length=100)
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class ReturnDebtCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    debt_id: int
    account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class DepositSavingCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    from_account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    goal_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class WithdrawSavingCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    to_account_id: int
    amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    goal_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    source: TransactionSource = TransactionSource.MANUAL_WEB
    idempotency_key: str | None = Field(default=None, max_length=64)


class CreateGoalCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int
    name: str = Field(min_length=1, max_length=60)
    target_amount: Annotated[Decimal, Field(gt=0, le=MAX_FINANCIAL_AMOUNT, decimal_places=2)]
    target_date: date | None = None


# -----------------------------------------------------------------------------
# DTO / OUTPUT CONTRACTS
# -----------------------------------------------------------------------------

class AccountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    icon: str
    balance: Decimal
    currency: str = "UZS"
    is_savings: bool
    is_active: bool
    sort_order: int


class CategoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    name: str
    icon: str
    type: str
    is_active: bool
    sort_order: int


class TransactionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_id: int
    type: str
    amount: Decimal
    currency: str = "UZS"
    exchange_rate: Decimal = Decimal("1.0")
    description: str | None
    category_id: int | None
    related_account_id: int | None
    debt_id: int | None
    created_at: datetime
