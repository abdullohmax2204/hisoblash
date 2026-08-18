"""Inline keyboard builders for all bot screens."""

from decimal import Decimal
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.config import settings
from app.database.models.account import Account
from app.database.models.category import Category
from app.database.models.debt import Debt
from app.database.models.saving_goal import SavingGoal
from app.database.models.transaction import Transaction, TransactionType


def format_amount(amount: int | float | Decimal) -> str:
    """Format a number with space as thousands separator.
    Example: 2850000 -> '2 850 000'
    """
    if isinstance(amount, Decimal):
        amount = int(amount)
    return f"{int(amount):,}".replace(",", " ")


# ──────────────────────────────────────────────
# Main Menu
# ──────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu shown after /start."""
    builder = InlineKeyboardBuilder()

    # Add Telegram Mini App launch button if webapp_url is configured
    if settings.webapp_url:
        builder.row(
            InlineKeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        )

    builder.row(
        InlineKeyboardButton(text="💰 Доход", callback_data="menu:income"),
        InlineKeyboardButton(text="💸 Расход", callback_data="menu:expense"),
    )
    builder.row(
        InlineKeyboardButton(text="🏦 Банк", callback_data="menu:bank"),
        InlineKeyboardButton(text="💵 Накопления", callback_data="menu:savings"),
    )
    builder.row(
        InlineKeyboardButton(text="🤝 Долги", callback_data="menu:debts"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="menu:statistics"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 История", callback_data="menu:history"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Navigation, Confirmations & Comments
# ──────────────────────────────────────────────

def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Back to Main Menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button for multi-step operations."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with Skip comment and Cancel."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Пропустить ➡️", callback_data="action:skip_comment"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


def tx_success_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard with quick Undo button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Отменить эту операцию", callback_data=f"tx:undo:{tx_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Quick Amount Chips
# ──────────────────────────────────────────────

def quick_amounts_keyboard(
    amounts: list[int], callback_prefix: str
) -> InlineKeyboardMarkup:
    """Quick amount chips in 3 columns."""
    builder = InlineKeyboardBuilder()
    row_btns = []
    for amt in amounts:
        btn_text = f"{format_amount(amt)}"
        row_btns.append(
            InlineKeyboardButton(
                text=btn_text, callback_data=f"{callback_prefix}:{amt}"
            )
        )
        if len(row_btns) == 3:
            builder.row(*row_btns)
            row_btns = []
    if row_btns:
        builder.row(*row_btns)

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Income Savings Percent Selection
# ──────────────────────────────────────────────

def income_savings_percent_keyboard(income_amount: Decimal) -> InlineKeyboardMarkup:
    """Percentages from 0% to 100% with exact money amounts."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="0% (0 сум — не откладывать)",
            callback_data="inc_sav:0",
        )
    )

    percentages = [10, 20, 30, 50]
    row_btns = []
    for pct in percentages:
        amount_part = (income_amount * Decimal(pct) / Decimal(100)).quantize(Decimal("1"))
        row_btns.append(
            InlineKeyboardButton(
                text=f"{pct}% ({format_amount(amount_part)} сум)",
                callback_data=f"inc_sav:{pct}",
            )
        )
        if len(row_btns) == 2:
            builder.row(*row_btns)
            row_btns = []
    if row_btns:
        builder.row(*row_btns)

    builder.row(
        InlineKeyboardButton(
            text=f"100% ({format_amount(income_amount)} сум — всё)",
            callback_data="inc_sav:100",
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Categories
# ──────────────────────────────────────────────

def categories_keyboard(
    categories: list[Category], callback_prefix: str
) -> InlineKeyboardMarkup:
    """Build a 2-column grid from categories."""
    builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(
            text=f"{cat.icon} {cat.name}",
            callback_data=f"{callback_prefix}:{cat.id}",
        )
        for cat in categories
    ]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            builder.row(buttons[i], buttons[i + 1])
        else:
            builder.row(buttons[i])

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Accounts & Bank
# ──────────────────────────────────────────────

def bank_menu_keyboard() -> InlineKeyboardMarkup:
    """Bank screen actions."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Перевод между счетами", callback_data="menu:transfer"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def accounts_keyboard(
    accounts: list[Account], callback_prefix: str
) -> InlineKeyboardMarkup:
    """Build a list of accounts."""
    builder = InlineKeyboardBuilder()
    for acc in accounts:
        builder.row(
            InlineKeyboardButton(
                text=f"{acc.icon} {acc.name} ({format_amount(acc.balance)} сум)",
                callback_data=f"{callback_prefix}:{acc.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="action:cancel"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Debts
# ──────────────────────────────────────────────

def debts_menu_keyboard() -> InlineKeyboardMarkup:
    """Debts submenu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Дать в долг", callback_data="debt:give"),
        InlineKeyboardButton(text="💰 Вернуть долг", callback_data="debt:return_select"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мне должны", callback_data="debt:list_given"),
        InlineKeyboardButton(text="💸 Я должен", callback_data="debt:list_taken"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def debts_list_keyboard(
    debts: list[Debt], callback_prefix: str
) -> InlineKeyboardMarkup:
    """Build a keyboard from a list of debts."""
    builder = InlineKeyboardBuilder()
    for debt in debts:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {debt.person_name} — {format_amount(debt.remaining_amount)} сум",
                callback_data=f"{callback_prefix}:{debt.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:debts"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Savings
# ──────────────────────────────────────────────

def savings_menu_keyboard(has_goals: bool = False) -> InlineKeyboardMarkup:
    """Savings submenu with multi-goal buttons."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Отложить деньги", callback_data="savings:deposit"),
        InlineKeyboardButton(text="↩️ Вернуть деньги", callback_data="savings:withdraw"),
    )
    if has_goals:
        builder.row(
            InlineKeyboardButton(text="🎯 Мои цели", callback_data="savings:goals_list"),
            InlineKeyboardButton(text="➕ Добавить цель", callback_data="savings:add_goal"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🎯 Добавить цель", callback_data="savings:add_goal"),
        )
    builder.row(
        InlineKeyboardButton(text="📋 История накоплений", callback_data="savings:history"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def goals_list_keyboard(goals: list[SavingGoal]) -> InlineKeyboardMarkup:
    """List of all active goals for management."""
    builder = InlineKeyboardBuilder()
    for g in goals:
        builder.row(
            InlineKeyboardButton(
                text=f"🎯 {g.name} ({format_amount(g.target_amount)} сум)",
                callback_data=f"savings:goal_view:{g.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еще цель", callback_data="savings:add_goal"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в накопления", callback_data="menu:savings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def goal_detail_keyboard(goal_id: int) -> InlineKeyboardMarkup:
    """Detail view / actions for a single goal."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить цель", callback_data=f"savings:goal_delete:{goal_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ К списку целей", callback_data="savings:goals_list"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────

def statistics_period_keyboard() -> InlineKeyboardMarkup:
    """Period selection for statistics."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="stats:today"),
        InlineKeyboardButton(text="📅 Эта неделя", callback_data="stats:week"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 Этот месяц", callback_data="stats:month"),
        InlineKeyboardButton(text="📅 Всё время", callback_data="stats:all"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# History
# ──────────────────────────────────────────────

def history_list_keyboard(
    transactions: list[Transaction], page: int, has_more: bool
) -> InlineKeyboardMarkup:
    """List of transactions with detail view and pagination."""
    builder = InlineKeyboardBuilder()

    for tx in transactions:
        sign = "+" if tx.type in (TransactionType.INCOME.value, TransactionType.DEBT_RETURN.value) else "-"
        icon = "💰"
        name = "Операция"
        if tx.category:
            icon = tx.category.icon
            name = tx.category.name
        elif tx.debt:
            icon = "🤝"
            name = tx.debt.person_name
        elif tx.type == TransactionType.SAVING.value:
            icon = "💵"
            name = "Накопления"
        elif tx.type == TransactionType.SAVING_WITHDRAW.value:
            icon = "↩️"
            name = "Из накоплений"
        elif tx.type == TransactionType.TRANSFER.value:
            icon = "🔄"
            name = "Перевод"

        btn_text = f"{icon} {name} {sign}{format_amount(tx.amount)} сум"
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"tx:view:{tx.id}")
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"history:page:{page - 1}")
        )
    if has_more:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Далее", callback_data=f"history:page:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


def transaction_detail_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Action buttons for a single transaction (Delete, Back)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить операцию", callback_data=f"tx:delete:{transaction_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ К истории", callback_data="menu:history"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────

def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Settings screen."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Добавить счет", callback_data="settings:add_account"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сделать бэкап", callback_data="settings:backup"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"),
    )
    return builder.as_markup()
