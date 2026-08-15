"""FSM states for all multi-step operations."""

from aiogram.fsm.state import State, StatesGroup


class IncomeStates(StatesGroup):
    """States for adding income: category → amount → comment (opt) → account → savings percent."""

    select_category = State()
    enter_amount = State()
    enter_comment = State()
    select_account = State()
    select_savings_percent = State()


class ExpenseStates(StatesGroup):
    """States for adding expense: category → amount → comment (opt) → account."""

    select_category = State()
    enter_amount = State()
    enter_comment = State()
    select_account = State()


class TransferStates(StatesGroup):
    """States for transferring between accounts."""

    select_from_account = State()
    select_to_account = State()
    enter_amount = State()


class SavingStates(StatesGroup):
    """States for saving operations."""

    enter_amount = State()
    select_account = State()


class SavingWithdrawStates(StatesGroup):
    """States for withdrawing from savings."""

    enter_amount = State()
    select_account = State()


class SavingGoalStates(StatesGroup):
    """States for setting/editing savings goal."""

    enter_name = State()
    enter_target = State()


class DebtGiveStates(StatesGroup):
    """States for giving a debt: person → amount → account."""

    enter_person = State()
    enter_amount = State()
    select_account = State()


class DebtReturnStates(StatesGroup):
    """States for returning a debt: select debt → amount → account."""

    select_debt = State()
    enter_amount = State()
    select_account = State()


class AccountStates(StatesGroup):
    """States for account management."""

    enter_name = State()
    enter_icon = State()
    enter_initial_balance = State()
