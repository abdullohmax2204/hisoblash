"""Savings handler — deposit, withdraw, and multi-goal tracking with goal notifications, quick chips, and smart parsing."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    savings_menu_keyboard,
    goals_list_keyboard,
    goal_detail_keyboard,
    accounts_keyboard,
    quick_amounts_keyboard,
    tx_success_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import SavingStates, SavingWithdrawStates, SavingGoalStates
from app.core.parser import parse_amount
from app.database.models.transaction import TransactionType
from app.services.account_service import AccountService
from app.services.savings_service import SavingsService
from app.services.user_service import ensure_user_exists

router = Router(name="savings")
logger = logging.getLogger(__name__)

QUICK_SAVINGS_AMOUNTS = [100000, 300000, 500000, 1000000, 2000000, 5000000]


def make_progress_bar(current: Decimal, target: Decimal, length: int = 8) -> str:
    """Generate visual progress bar (e.g. [🟩🟩🟩⬜⬜⬜⬜⬜] 35%)."""
    if target <= Decimal("0"):
        return ""
    pct = min(int((current / target) * 100), 100)
    filled = min(int((current / target) * length), length)
    empty = length - filled
    bar = "🟩" * filled + "⬜" * empty
    return f"[{bar}] <b>{pct}%</b>"


@router.callback_query(F.data == "menu:savings")
async def show_savings_menu(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Show savings overview, all active goals with individual progress, and action buttons."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    savings_service = SavingsService(session)
    overview = await savings_service.get_multi_goals_overview(user.id)

    balance = overview["savings_balance"]
    lines = [
        "💵 <b>НАКОПЛЕНИЯ</b>\n",
        f"Накоплено: <b>{format_amount(balance)} сум</b>",
    ]

    if overview["has_goals"]:
        total_target = overview["total_target"]
        overall_bar = make_progress_bar(balance, total_target)
        lines.append(f"\n🎯 <b>Общая сумма всех целей:</b> {format_amount(total_target)} сум")
        lines.append(f"📊 <b>Общий прогресс:</b> {overall_bar}\n")

        load_analysis = await savings_service.get_financial_load_analysis(user.id)
        if load_analysis["goals"]:
            lines.append(
                f"⚡ <b>Нагрузка на зарплату:</b> {load_analysis['stress_icon']} <b>{load_analysis['stress_pct']}%</b> ({load_analysis['stress_level_ru']})"
            )
            lines.append(
                f"💳 Откладывать: <b>{format_amount(load_analysis['total_required_monthly'])} сум/мес</b> (или {format_amount(load_analysis['total_required_15day'])} сум каждые 15 дн)\n"
            )

        lines.append("<b>Ваши цели:</b>")

        for item in overview["goals"]:
            g = item["goal"]
            target = item["target"]
            date_str = f" (до {g.target_date.strftime('%d.%m.%Y')})" if g.target_date else ""
            if item["is_funded"]:
                lines.append(f"✅ <b>{g.name}</b>{date_str}: {format_amount(target)} сум — <i>Накоплено! 🎉</i>")
            else:
                bar = make_progress_bar(balance, target, length=6)
                lines.append(f"🎯 <b>{g.name}</b>{date_str}: {format_amount(target)} сум\n   {bar}")
    else:
        lines.append("\n<i>🎯 Цели пока не добавлены. Добавьте цели, чтобы видеть общий прогресс накоплений!</i>")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=savings_menu_keyboard(has_goals=overview["has_goals"]),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── MULTI-GOALS MANAGEMENT ───────────────────

@router.callback_query(F.data == "savings:goals_list")
async def show_goals_list(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show list of all goals to view or delete."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    savings_service = SavingsService(session)
    goals = await savings_service.get_active_goals(user.id)

    if not goals:
        await callback.message.edit_text(
            "🎯 <b>Мои цели</b>\n\nУ вас пока нет активных целей.",
            reply_markup=savings_menu_keyboard(has_goals=False),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = "🎯 <b>Мои цели накоплений:</b>\n<i>Выберите цель для просмотра или удаления:</i>"
    await callback.message.edit_text(
        text,
        reply_markup=goals_list_keyboard(goals),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("savings:goal_view:"))
async def view_goal_detail(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show detail of a single goal."""
    goal_id = int(callback.data.split(":")[2])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    savings_service = SavingsService(session)
    goal = await savings_service.get_goal_by_id(goal_id, user.id)
    savings_acc = await savings_service.get_savings_account(user.id)

    if not goal:
        await callback.message.edit_text("⚠️ Цель не найдена.", reply_markup=savings_menu_keyboard())
        await callback.answer()
        return

    pct_text = make_progress_bar(savings_acc.balance, goal.target_amount)
    status = "🎉 <b>Средств достаточно! Можно покупать!</b>" if savings_acc.balance >= goal.target_amount else f"Осталось: <b>{format_amount(goal.target_amount - savings_acc.balance)} сум</b>"

    text = (
        f"🎯 <b>Цель: {goal.name}</b>\n\n"
        f"Нужная сумма: <b>{format_amount(goal.target_amount)} сум</b>\n"
        f"Накоплено всего: <b>{format_amount(savings_acc.balance)} сум</b>\n"
        f"Прогресс: {pct_text}\n\n"
        f"{status}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=goal_detail_keyboard(goal.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("savings:goal_delete:"))
async def delete_goal_action(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Delete a goal."""
    goal_id = int(callback.data.split(":")[2])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    savings_service = SavingsService(session)
    await savings_service.delete_goal(user.id, goal_id)

    await callback.answer("✅ Цель удалена.", show_alert=True)
    await show_goals_list(callback, session)


@router.callback_query(F.data == "savings:add_goal")
async def start_add_goal(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 1 Goal: Ask goal name."""
    await state.set_state(SavingGoalStates.enter_name)
    await callback.message.edit_text(
        "🎯 <b>Добавление цели</b>\n\n"
        "На что именно вы хотите накопить?\n"
        "<i>(Например: Новый ноутбук, Машина, Подушка безопасности, Отпуск)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SavingGoalStates.enter_name)
async def goal_name_entered(
    message: Message, state: FSMContext
) -> None:
    """Step 2 Goal: Ask target amount."""
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Введите название цели:")
        return

    await state.update_data(goal_name=name)
    await state.set_state(SavingGoalStates.enter_target)

    await message.answer(
        f"Цель: <b>{name}</b>\n\n"
        "Сколько денег нужно накопить на эту цель?\n"
        "<i>(Например: 15000000, 15м)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(SavingGoalStates.enter_target)
async def goal_target_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3 Goal: Save goal and show overview."""
    target = parse_amount(message.text)
    if target is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 15000000, 15м)</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )

    name = data["goal_name"]
    savings_service = SavingsService(session)
    goal = await savings_service.create_goal(user.id, name=name, target_amount=target)
    savings_account = await savings_service.get_savings_account(user.id)

    pct_text = make_progress_bar(savings_account.balance, goal.target_amount)

    text = (
        "✅ <b>Цель успешно добавлена!</b>\n\n"
        f"🎯 <b>{goal.name}</b>\n"
        f"Нужно: <b>{format_amount(goal.target_amount)} сум</b>\n"
        f"Уже накоплено: <b>{format_amount(savings_account.balance)} сум</b>\n"
        f"Прогресс: {pct_text}"
    )

    await message.answer(
        text,
        reply_markup=savings_menu_keyboard(has_goals=True),
        parse_mode="HTML",
    )


# ─── DEPOSIT FLOW ─────────────────────────────

@router.callback_query(F.data == "savings:deposit")
async def start_deposit_flow(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 1 Deposit: Ask amount to deposit with quick chips."""
    await state.set_state(SavingStates.enter_amount)
    await callback.message.edit_text(
        "➕ <b>Отложить в накопления</b>\n\n"
        "<b>Выберите быструю сумму или введите свою:</b>\n"
        "<i>(Поддерживаются: 500к, 1м, 2м)</i>",
        reply_markup=quick_amounts_keyboard(QUICK_SAVINGS_AMOUNTS, callback_prefix="sav_dep_quick"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SavingStates.enter_amount, F.data.startswith("sav_dep_quick:"))
async def deposit_quick_amount_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1b: Quick chip selected."""
    amount_str = callback.data.split(":")[1]
    amount = Decimal(amount_str)
    await prompt_deposit_account(callback.message, session, state, amount, is_callback=True)
    await callback.answer()


@router.message(SavingStates.enter_amount)
async def deposit_amount_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2 Deposit: Ask source account."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 500000, 500к, 1м)</i>",
            reply_markup=quick_amounts_keyboard(QUICK_SAVINGS_AMOUNTS, callback_prefix="sav_dep_quick"),
            parse_mode="HTML",
        )
        return

    await prompt_deposit_account(message, session, state, amount, is_callback=False)


async def prompt_deposit_account(
    message_or_msg, session: AsyncSession, state: FSMContext, amount: Decimal, is_callback: bool
) -> None:
    await state.update_data(amount=str(amount))

    user = await ensure_user_exists(
        session=session,
        telegram_id=message_or_msg.chat.id,
        name=message_or_msg.chat.full_name or "User",
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    text = (
        f"Отложить: <b>+{format_amount(amount)} сум</b>\n\n"
        "С какого счета списать?"
    )

    await state.set_state(SavingStates.select_account)
    if is_callback:
        await message_or_msg.edit_text(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="sav_dep_acc"),
            parse_mode="HTML",
        )
    else:
        await message_or_msg.answer(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="sav_dep_acc"),
            parse_mode="HTML",
        )


@router.callback_query(SavingStates.select_account, F.data.startswith("sav_dep_acc:"))
async def deposit_account_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3 Deposit: Record deposit and show result with celebration if goal reached."""
    account_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    amount = Decimal(data["amount"])

    savings_service = SavingsService(session)
    try:
        tx, src_acc, sav_acc, newly_reached = await savings_service.deposit(
            user_id=user.id,
            source_account_id=account_id,
            amount=amount,
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
        "✅ <b>Деньги отложены</b>\n",
        f"Сумма: <b>+{format_amount(amount)} сум</b>",
        f"Списано с: {src_acc.icon} {src_acc.name} (остаток: {format_amount(src_acc.balance)} сум)",
        f"💵 Всего в накоплениях: <b>{format_amount(sav_acc.balance)} сум</b>",
    ]

    if newly_reached:
        lines.append("\n━━━━━━━━━━━━")
        for g in newly_reached:
            lines.append(f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> Вы накопили достаточно средств для цели:\n🎯 <b>«{g.name}»</b> ({format_amount(g.target_amount)} сум)!")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── WITHDRAW FLOW ────────────────────────────

@router.callback_query(F.data == "savings:withdraw")
async def start_withdraw_flow(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 1 Withdraw: Ask amount to withdraw."""
    await state.set_state(SavingWithdrawStates.enter_amount)
    await callback.message.edit_text(
        "↩️ <b>Вернуть деньги из накоплений</b>\n\n"
        "<b>Выберите быструю сумму или введите свою:</b>\n"
        "<i>(Поддерживаются: 100к, 500к, 1м)</i>",
        reply_markup=quick_amounts_keyboard(QUICK_SAVINGS_AMOUNTS, callback_prefix="sav_wdr_quick"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SavingWithdrawStates.enter_amount, F.data.startswith("sav_wdr_quick:"))
async def withdraw_quick_amount_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1b: Quick chip selected for withdraw."""
    amount_str = callback.data.split(":")[1]
    amount = Decimal(amount_str)
    await prompt_withdraw_account(callback.message, session, state, amount, is_callback=True)
    await callback.answer()


@router.message(SavingWithdrawStates.enter_amount)
async def withdraw_amount_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2 Withdraw: Ask destination account."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Введите корректную сумму цифрами:\n<i>(Например: 200000, 200к, 1м)</i>",
            reply_markup=quick_amounts_keyboard(QUICK_SAVINGS_AMOUNTS, callback_prefix="sav_wdr_quick"),
            parse_mode="HTML",
        )
        return

    await prompt_withdraw_account(message, session, state, amount, is_callback=False)


async def prompt_withdraw_account(
    message_or_msg, session: AsyncSession, state: FSMContext, amount: Decimal, is_callback: bool
) -> None:
    await state.update_data(amount=str(amount))

    user = await ensure_user_exists(
        session=session,
        telegram_id=message_or_msg.chat.id,
        name=message_or_msg.chat.full_name or "User",
    )
    acc_service = AccountService(session)
    accounts = await acc_service.get_user_accounts(user.id, include_savings=False)

    text = (
        f"Вернуть: <b>{format_amount(amount)} сум</b>\n\n"
        "На какой счет зачислить?"
    )

    await state.set_state(SavingWithdrawStates.select_account)
    if is_callback:
        await message_or_msg.edit_text(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="sav_wdr_acc"),
            parse_mode="HTML",
        )
    else:
        await message_or_msg.answer(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="sav_wdr_acc"),
            parse_mode="HTML",
        )


@router.callback_query(SavingWithdrawStates.select_account, F.data.startswith("sav_wdr_acc:"))
async def withdraw_account_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3 Withdraw: Record withdraw and show result."""
    account_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    amount = Decimal(data["amount"])

    savings_service = SavingsService(session)
    try:
        tx, dest_acc, sav_acc = await savings_service.withdraw(
            user_id=user.id,
            dest_account_id=account_id,
            amount=amount,
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
        "✅ <b>Деньги возвращены из накоплений</b>\n\n"
        f"Сумма: <b>{format_amount(amount)} сум</b>\n\n"
        f"Зачислено на: {dest_acc.icon} {dest_acc.name} (баланс: {format_amount(dest_acc.balance)} сум)\n"
        f"💵 Осталось в накоплениях: <b>{format_amount(sav_acc.balance)} сум</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── SAVINGS HISTORY ──────────────────────────

@router.callback_query(F.data == "savings:history")
async def show_savings_history(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show history of savings operations."""
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    savings_service = SavingsService(session)
    history = await savings_service.get_savings_history(user.id)

    if not history:
        await callback.message.edit_text(
            "📋 <b>История накоплений</b>\n\nОпераций пока нет.",
            reply_markup=savings_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = ["📋 <b>История накоплений:</b>\n"]
    for tx in history:
        date_str = tx.created_at.strftime("%d.%m.%Y %H:%M")
        desc = f" ({tx.description})" if tx.description else ""
        if tx.type == TransactionType.SAVING.value:
            lines.append(f"➕ <b>+{format_amount(tx.amount)} сум</b> — {date_str}{desc}")
        else:
            lines.append(f"↩️ <b>-{format_amount(tx.amount)} сум</b> — {date_str}{desc}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=savings_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
