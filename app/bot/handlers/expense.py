"""Expense handler — category -> amount (with quick chips & smart parsing) -> comment -> account -> save."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    categories_keyboard,
    accounts_keyboard,
    skip_comment_keyboard,
    quick_amounts_keyboard,
    tx_success_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import ExpenseStates
from app.core.parser import parse_amount
from app.services.account_service import AccountService
from app.services.category_service import CategoryService
from app.services.finance_service import FinanceService
from app.services.user_service import ensure_user_exists

router = Router(name="expense")
logger = logging.getLogger(__name__)

QUICK_EXPENSE_AMOUNTS = [15000, 30000, 50000, 100000, 200000, 500000]


@router.callback_query(F.data == "menu:expense")
async def start_expense_flow(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1: Choose category for expense."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    cat_service = CategoryService(session)
    categories = await cat_service.get_categories_by_type(user.id, "EXPENSE")

    await state.set_state(ExpenseStates.select_category)
    await callback.message.edit_text(
        "💸 <b>Расход</b>\n\nВыберите категорию:",
        reply_markup=categories_keyboard(categories, callback_prefix="exp_cat"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExpenseStates.select_category, F.data.startswith("exp_cat:"))
async def expense_category_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2: Category selected, ask for amount with quick chips."""
    cat_id = int(callback.data.split(":")[1])
    cat_service = CategoryService(session)
    category = await cat_service.get_category_by_id(cat_id)

    await state.update_data(category_id=cat_id, category_name=category.name, category_icon=category.icon)
    await state.set_state(ExpenseStates.enter_amount)

    await callback.message.edit_text(
        f"💸 <b>Расход</b>: {category.icon} {category.name}\n\n"
        "<b>Выберите быструю сумму или введите свою:</b>\n"
        "<i>(Поддерживаются: 50к, 150к, 25000+18000)</i>",
        reply_markup=quick_amounts_keyboard(QUICK_EXPENSE_AMOUNTS, callback_prefix="exp_quick"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExpenseStates.enter_amount, F.data.startswith("exp_quick:"))
async def expense_quick_amount_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 2b: Quick amount chip clicked."""
    amount_str = callback.data.split(":")[1]
    amount = Decimal(amount_str)

    await state.update_data(amount=str(amount))
    await state.set_state(ExpenseStates.enter_comment)

    await callback.message.edit_text(
        f"Сумма: <b>-{format_amount(amount)} сум</b>\n\n"
        "💬 <b>Добавьте комментарий</b> (на что именно потрачено):\n"
        "<i>Или нажмите «Пропустить ➡️»</i>",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ExpenseStates.enter_amount)
async def expense_amount_entered(
    message: Message, state: FSMContext
) -> None:
    """Step 3: Amount received via text input (using smart parser)."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Пожалуйста, введите корректную сумму цифрами.\n"
            "<i>(Например: 45000, 45к, 150к или 25000+18000)</i>",
            reply_markup=quick_amounts_keyboard(QUICK_EXPENSE_AMOUNTS, callback_prefix="exp_quick"),
            parse_mode="HTML",
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(ExpenseStates.enter_comment)

    await message.answer(
        f"Сумма: <b>-{format_amount(amount)} сум</b>\n\n"
        "💬 <b>Добавьте комментарий</b> (на что именно потрачено):\n"
        "<i>Или нажмите «Пропустить ➡️»</i>",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(ExpenseStates.enter_comment, F.data == "action:skip_comment")
async def expense_skip_comment(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4a: Comment skipped."""
    await state.update_data(comment=None)
    await prompt_expense_account_selection(callback.message, session, state, is_callback=True)
    await callback.answer()


@router.message(ExpenseStates.enter_comment)
async def expense_comment_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4b: Comment entered."""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await prompt_expense_account_selection(message, session, state, is_callback=False)


async def prompt_expense_account_selection(
    message_or_msg, session: AsyncSession, state: FSMContext, is_callback: bool
) -> None:
    """Show account selection for expense."""
    data = await state.get_data()
    amount = Decimal(data["amount"])
    comment = data.get("comment")

    user = await ensure_user_exists(
        session=session,
        telegram_id=message_or_msg.chat.id,
        name=message_or_msg.chat.full_name or "User",
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    comment_line = f"\n💬 <i>{comment}</i>\n" if comment else ""
    text = (
        f"Сумма: <b>-{format_amount(amount)} сум</b>{comment_line}\n"
        "С какого счета списать?"
    )

    await state.set_state(ExpenseStates.select_account)
    if is_callback:
        await message_or_msg.edit_text(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="exp_acc"),
            parse_mode="HTML",
        )
    else:
        await message_or_msg.answer(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="exp_acc"),
            parse_mode="HTML",
        )


@router.callback_query(ExpenseStates.select_account, F.data.startswith("exp_acc:"))
async def expense_account_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 5: Account selected, record expense and display result."""
    account_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    amount = Decimal(data["amount"])
    category_id = data.get("category_id")
    cat_icon = data.get("category_icon", "💸")
    cat_name = data.get("category_name", "Расход")
    comment = data.get("comment")

    finance_service = FinanceService(session)
    try:
        tx, account = await finance_service.add_expense(
            user_id=user.id,
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            description=comment,
            source="bot_keyboard",
        )
    except ValueError as e:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка</b>: {e}",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [
        "✅ <b>Расход записан</b>\n",
        f"{cat_icon} {cat_name}",
        f"<b>-{format_amount(amount)} сум</b>",
    ]
    if comment:
        lines.append(f"📝 <i>«{comment}»</i>")

    lines.append(f"\n{account.icon} {account.name}\nОстаток:\n<b>{format_amount(account.balance)} сум</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()
