"""Debts handler — lend money, borrow money, return debt, view debts."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    debts_menu_keyboard,
    debts_list_keyboard,
    accounts_keyboard,
    tx_success_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import DebtGiveStates, DebtReturnStates
from app.core.parser import parse_amount
from app.database.models.debt import DebtType
from app.services.account_service import AccountService
from app.services.debt_service import DebtService
from app.services.user_service import ensure_user_exists

router = Router(name="debts")
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:debts")
async def show_debts_menu(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Show debts submenu."""
    await state.clear()
    await callback.message.edit_text(
        "🤝 <b>Управление долгами</b>\n\nВыберите действие:",
        reply_markup=debts_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── GIVE DEBT (ДАВАТЬ В ДОЛГ) ─────────────────

@router.callback_query(F.data == "debt:give")
async def start_give_debt(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 1: Ask person name."""
    await state.set_state(DebtGiveStates.enter_person)
    await callback.message.edit_text(
        "➕ <b>Дать в долг</b>\n\nКому вы даете в долг?\n<i>(Введите имя человека)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DebtGiveStates.enter_person)
async def give_debt_person_entered(
    message: Message, state: FSMContext
) -> None:
    """Step 2: Ask amount."""
    person_name = message.text.strip()
    if not person_name:
        await message.answer("⚠️ Введите имя человека:")
        return

    await state.update_data(person_name=person_name)
    await state.set_state(DebtGiveStates.enter_amount)
    await message.answer(
        f"Кому: <b>{person_name}</b>\n\nКакую сумму даете в долг?\n<i>Например: 300000</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(DebtGiveStates.enter_amount)
async def give_debt_amount_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3: Ask account."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 300000, 300к)</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(amount=str(amount))

    user = await ensure_user_exists(
        session=session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    await state.set_state(DebtGiveStates.select_account)
    await message.answer(
        f"Сумма: <b>{format_amount(amount)} сум</b>\n\nС какого счета списать?",
        reply_markup=accounts_keyboard(accounts, callback_prefix="dbt_give_acc"),
        parse_mode="HTML",
    )


@router.callback_query(DebtGiveStates.select_account, F.data.startswith("dbt_give_acc:"))
async def give_debt_account_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4: Save debt given."""
    account_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    person_name = data["person_name"]
    amount = Decimal(data["amount"])

    debt_service = DebtService(session)
    try:
        debt, tx, account = await debt_service.give_debt(
            user_id=user.id,
            person_name=person_name,
            amount=amount,
            account_id=account_id,
        )
    except ValueError as e:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка</b>: {e}",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = (
        "✅ <b>Долг записан</b>\n\n"
        f"👤 <b>{person_name}</b> должен:\n"
        f"<b>{format_amount(amount)} сум</b>\n\n"
        f"Списано с: {account.icon} {account.name}\n"
        f"Остаток на счете: {format_amount(account.balance)} сум"
    )

    await callback.message.edit_text(
        text,
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── RETURN DEBT (ВЕРНУТЬ ДОЛГ) ────────────────

@router.callback_query(F.data == "debt:return_select")
async def start_return_debt(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1: Select which debt to return."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    debt_service = DebtService(session)
    active_debts = await debt_service.get_active_debts(user.id, DebtType.GIVEN.value)

    if not active_debts:
        await callback.message.edit_text(
            "📋 <b>Возврат долга</b>\n\nУ вас нет активных должников (вам никто не должен).",
            reply_markup=debts_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await state.set_state(DebtReturnStates.select_debt)
    await callback.message.edit_text(
        "💰 <b>Возврат долга</b>\n\nКто возвращает деньги?",
        reply_markup=debts_list_keyboard(active_debts, callback_prefix="dbt_ret"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(DebtReturnStates.select_debt, F.data.startswith("dbt_ret:"))
async def debt_selected_for_return(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2: Debt selected, ask how much returned."""
    debt_id = int(callback.data.split(":")[1])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    debt_service = DebtService(session)
    debt = await debt_service.get_debt_by_id(debt_id, user.id)

    if not debt:
        await callback.message.edit_text("⚠️ Долг не найден.", reply_markup=debts_menu_keyboard())
        await callback.answer()
        return

    await state.update_data(debt_id=debt_id, person_name=debt.person_name, remaining=str(debt.remaining_amount))
    await state.set_state(DebtReturnStates.enter_amount)

    await callback.message.edit_text(
        f"👤 <b>{debt.person_name}</b> должен: <b>{format_amount(debt.remaining_amount)} сум</b>\n\n"
        "Сколько денег вернул?\n"
        f"<i>(Введите сумму до {format_amount(debt.remaining_amount)})</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DebtReturnStates.enter_amount)
async def debt_return_amount_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3: Amount entered, ask account."""
    data = await state.get_data()
    remaining = Decimal(data.get("remaining", "0"))

    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 100000, 100к)</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    if amount > remaining:
        await message.answer(
            f"⚠️ Сумма не может превышать остаток долга ({format_amount(remaining)} сум).\nВведите сумму еще раз:",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(amount=str(amount))

    user = await ensure_user_exists(
        session=session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    await state.set_state(DebtReturnStates.select_account)
    await message.answer(
        f"Возврат: <b>+{format_amount(amount)} сум</b>\n\nНа какой счет зачислить?",
        reply_markup=accounts_keyboard(accounts, callback_prefix="dbt_ret_acc"),
        parse_mode="HTML",
    )


@router.callback_query(DebtReturnStates.select_account, F.data.startswith("dbt_ret_acc:"))
async def debt_return_account_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4: Save debt return."""
    account_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    debt_id = data["debt_id"]
    amount = Decimal(data["amount"])

    debt_service = DebtService(session)
    try:
        debt, tx, account = await debt_service.return_debt(
            user_id=user.id,
            debt_id=debt_id,
            amount=amount,
            account_id=account_id,
        )
    except ValueError as e:
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка</b>: {e}",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    status_text = f"Остаток долга: <b>{format_amount(debt.remaining_amount)} сум</b>" if not debt.is_settled else "🎉 <b>Долг полностью погашен!</b>"

    text = (
        "✅ <b>Возврат долга записан</b>\n\n"
        f"👤 {debt.person_name}\n"
        f"+{format_amount(amount)} сум\n\n"
        f"{status_text}\n\n"
        f"Зачислено на: {account.icon} {account.name}\n"
        f"Баланс счета: <b>{format_amount(account.balance)} сум</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── LIST DEBTS (МНЕ ДОЛЖНЫ / Я ДОЛЖЕН) ────────

@router.callback_query(F.data == "debt:list_given")
async def list_debts_given(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show list of debts owed to user."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    debt_service = DebtService(session)
    debts = await debt_service.get_active_debts(user.id, DebtType.GIVEN.value)

    if not debts:
        await callback.message.edit_text(
            "📋 <b>Мне должны</b>\n\nАктивных долгов нет 🎉",
            reply_markup=debts_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    total = sum((d.remaining_amount for d in debts), Decimal("0"))
    lines = ["📋 <b>МНЕ ДОЛЖНЫ:</b>\n"]
    for d in debts:
        lines.append(f"👤 <b>{d.person_name}</b>: {format_amount(d.remaining_amount)} сум (из {format_amount(d.original_amount)})")

    lines.append(f"\n━━━━━━━━━━━━\n<b>Всего мне должны:</b> {format_amount(total)} сум")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=debts_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "debt:list_taken")
async def list_debts_taken(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show list of debts user owes."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    debt_service = DebtService(session)
    debts = await debt_service.get_active_debts(user.id, DebtType.TAKEN.value)

    if not debts:
        await callback.message.edit_text(
            "💸 <b>Я должен</b>\n\nУ вас нет задолженностей 🎉",
            reply_markup=debts_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    total = sum((d.remaining_amount for d in debts), Decimal("0"))
    lines = ["💸 <b>Я ДОЛЖЕН:</b>\n"]
    for d in debts:
        lines.append(f"👤 <b>{d.person_name}</b>: {format_amount(d.remaining_amount)} сум")

    lines.append(f"\n━━━━━━━━━━━━\n<b>Всего я должен:</b> {format_amount(total)} сум")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=debts_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
