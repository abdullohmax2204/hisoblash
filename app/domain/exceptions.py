"""Domain-level exceptions for Hisoblash Core.

All business logic errors must inherit from FinanceDomainError.
Adapters (REST API, Telegram Bot, etc.) map these exceptions to their respective protocols.
"""


class FinanceDomainError(Exception):
    """Base exception for all financial domain errors."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class InsufficientFundsError(FinanceDomainError):
    """Raised when an account balance is lower than the required amount."""
    def __init__(self, available: str, required: str, account_name: str = "Счет"):
        msg = f"Недостаточно средств на счете '{account_name}'. Доступно: {available}, требуется: {required}."
        super().__init__(msg, code="INSUFFICIENT_FUNDS")
        self.available = available
        self.required = required
        self.account_name = account_name


class EntityNotFoundError(FinanceDomainError):
    """Raised when a requested account, category, debt, or transaction is not found."""
    def __init__(self, entity_type: str, entity_id: int | str):
        msg = f"{entity_type} с ID {entity_id} не найден."
        super().__init__(msg, code="NOT_FOUND")
        self.entity_type = entity_type
        self.entity_id = entity_id


class CurrencyMismatchError(FinanceDomainError):
    """Raised when an operation is attempted across accounts of differing currencies without a valid rate."""
    def __init__(self, source_curr: str, target_curr: str):
        msg = f"Несовпадение валют: {source_curr} и {target_curr}. Требуется конвертация."
        super().__init__(msg, code="CURRENCY_MISMATCH")
        self.source_curr = source_curr
        self.target_curr = target_curr


class DuplicateRequestError(FinanceDomainError):
    """Raised when an idempotency key matches an already processed transaction."""
    def __init__(self, idempotency_key: str):
        msg = f"Операция с ключом {idempotency_key} уже обработана."
        super().__init__(msg, code="DUPLICATE_REQUEST")
        self.idempotency_key = idempotency_key


class InvalidAmountError(FinanceDomainError):
    """Raised when transaction amount is non-positive or exceeds maximum allowable limit."""
    def __init__(self, amount: str, reason: str = "Сумма должна быть больше нуля"):
        super().__init__(f"{reason}: {amount}", code="INVALID_AMOUNT")
        self.amount = amount
