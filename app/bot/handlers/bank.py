"""Bank handler — displays all accounts, overview, and transfers between accounts."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    bank_menu_keyboard,
    accounts_keyboard,
    quick_amounts_keyboard,
    tx_success_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import TransferStates
from app.core.parser import parse_amount
from app.services.account_service import AccountService
from app.services.finance_service import FinanceService
from app.services.user_service import ensure_user_exists

router = Router(name="bank")
logger = logging.getLogger(__name__)

QUICK_TRANSFER_AMOUNTS = [50000, 100000, 200000, 500000, 1000000, 2000000]


@router.callback_query(F.data == "menu:bank")
async def show_bank(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Show user's bank accounts, total capital, available funds, savings, and debts."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    acc_service = AccountService(session)
    summary = await acc_service.get_bank_summary(user.id)

    lines = ["🏦 <b>МОИ ДЕНЬГИ</b>\n"]

    for acc in summary["regular_accounts"]:
        lines.append(f"{acc.icon} {acc.name}\n<b>{format_amount(acc.balance)} сум</b>\n")

    lines.append(f"💵 Накопления\n<b>{format_amount(summary['savings_balance'])} сум</b>\n")

    lines.append("━━━━━━━━━━━━\n")
    lines.append(f"💰 <b>Общий капитал:</b>\n{format_amount(summary['total_capital'])} сум\n")
    lines.append(f"💳 <b>Доступно:</b>\n{format_amount(summary['available_funds'])} сум\n")
    lines.append(f"💵 <b>Накоплено:</b>\n{format_amount(summary['savings_balance'])} сум")

    if summary["debts_given"] > 0:
        lines.append(f"\n🤝 <b>Мне должны:</b>\n{format_amount(summary['debts_given'])} сум")
    if summary["debts_taken"] > 0:
        lines.append(f"\n💸 <b>Я должен:</b>\n{format_amount(summary['debts_taken'])} сум")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=bank_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── TRANSFER BETWEEN ACCOUNTS FLOW ───────────

@router.callback_query(F.data == "menu:transfer")
async def start_transfer_flow(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1 Transfer: Select source account."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    if len(accounts) < 2:
        await callback.message.edit_text(
            "⚠️ Для перевода нужно минимум 2 счета.\nДобавьте еще один счет в Настройках ⚙️",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(TransferStates.select_from_account)
    await callback.message.edit_text(
        "🔄 <b>Перевод между своими счетами</b>\n\nС какого счета перевести?",
        reply_markup=accounts_keyboard(accounts, callback_prefix="tr_from"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TransferStates.select_from_account, F.data.startswith("tr_from:"))
async def transfer_from_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2 Transfer: Select destination account."""
    from_acc_id = int(callback.data.split(":")[1])
    await state.update_data(from_account_id=from_acc_id)

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    acc_service = AccountService(session)
    all_accounts = await acc_service.get_user_accounts(user.id, include_savings=False)
    dest_accounts = [a for a in all_accounts if a.id != from_acc_id]

    await state.set_state(TransferStates.select_to_account)
    await callback.message.edit_text(
        "🔄 <b>Перевод</b>\n\nНа какой счет зачислить?",
        reply_markup=accounts_keyboard(dest_accounts, callback_prefix="tr_to"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TransferStates.select_to_account, F.data.startswith("tr_to:"))
async def transfer_to_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 3 Transfer: Ask amount."""
    to_acc_id = int(callback.data.split(":")[1])
    await state.update_data(to_account_id=to_acc_id)

    await state.set_state(TransferStates.enter_amount)
    await callback.message.edit_text(
        "🔄 <b>Перевод</b>\n\n"
        "<b>Выберите быструю сумму или введите свою:</b>\n"
        "<i>(Поддерживаются: 50к, 100к, 1м)</i>",
        reply_markup=quick_amounts_keyboard(QUICK_TRANSFER_AMOUNTS, callback_prefix="tr_quick"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TransferStates.enter_amount, F.data.startswith("tr_quick:"))
async def transfer_quick_amount_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4a: Quick amount selected."""
    amount_str = callback.data.split(":")[1]
    amount = Decimal(amount_str)
    await execute_transfer(callback.message, session, state, amount, is_callback=True)
    await callback.answer()


@router.message(TransferStates.enter_amount)
async def transfer_amount_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4b: Text amount entered."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 100000, 100к)</i>",
            reply_markup=quick_amounts_keyboard(QUICK_TRANSFER_AMOUNTS, callback_prefix="tr_quick"),
            parse_mode="HTML",
        )
        return
    await execute_transfer(message, session, state, amount, is_callback=False)


async def execute_transfer(
    message_or_msg, session: AsyncSession, state: FSMContext, amount: Decimal, is_callback: bool
) -> None:
    """Execute transfer transaction."""
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=message_or_msg.chat.id,
        name=message_or_msg.chat.full_name or "User",
    )

    from_id = data["from_account_id"]
    to_id = data["to_account_id"]

    finance_service = FinanceService(session)
    try:
        tx, from_acc, to_acc = await finance_service.transfer_between_accounts(
            user_id=user.id,
            from_account_id=from_id,
            to_account_id=to_id,
            amount=amount,
        )
    except ValueError as e:
        err_text = f"⚠️ <b>Ошибка</b>: {e}"
        if is_callback:
            await message_or_msg.edit_text(err_text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")
        else:
            await message_or_msg.answer(err_text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")
        return

    text = (
        "✅ <b>Перевод успешно выполнен!</b>\n\n"
        f"Сумма: <b>{format_amount(amount)} сум</b>\n\n"
        f"Откуда: {from_acc.icon} {from_acc.name} (остаток: {format_amount(from_acc.balance)} сум)\n"
        f"Куда:   {to_acc.icon} {to_acc.name} (баланс: {format_amount(to_acc.balance)} сум)\n\n"
        "<i>💰 Общий капитал не изменился.</i>"
    )

    if is_callback:
        await message_or_msg.edit_text(text, reply_markup=tx_success_keyboard(tx.id), parse_mode="HTML")
    else:
        await message_or_msg.answer(text, reply_markup=tx_success_keyboard(tx.id), parse_mode="HTML")
