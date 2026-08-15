"""Income handler — category -> amount (with quick chips & smart parsing) -> comment -> account -> savings percent -> save."""

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
    income_savings_percent_keyboard,
    tx_success_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import IncomeStates
from app.core.parser import parse_amount
from app.services.account_service import AccountService
from app.services.category_service import CategoryService
from app.services.finance_service import FinanceService
from app.services.savings_service import SavingsService
from app.services.user_service import ensure_user_exists

router = Router(name="income")
logger = logging.getLogger(__name__)

QUICK_INCOME_AMOUNTS = [200000, 500000, 1000000, 2000000, 5000000, 10000000]


@router.callback_query(F.data == "menu:income")
async def start_income_flow(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 1: Choose category for income."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    cat_service = CategoryService(session)
    categories = await cat_service.get_categories_by_type(user.id, "INCOME")

    await state.set_state(IncomeStates.select_category)
    await callback.message.edit_text(
        "💰 <b>Доход</b>\n\nВыберите категорию:",
        reply_markup=categories_keyboard(categories, callback_prefix="inc_cat"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(IncomeStates.select_category, F.data.startswith("inc_cat:"))
async def income_category_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 2: Category selected, ask for amount with quick chips."""
    cat_id = int(callback.data.split(":")[1])
    cat_service = CategoryService(session)
    category = await cat_service.get_category_by_id(cat_id)

    await state.update_data(category_id=cat_id, category_name=category.name, category_icon=category.icon)
    await state.set_state(IncomeStates.enter_amount)

    await callback.message.edit_text(
        f"💰 <b>Доход</b>: {category.icon} {category.name}\n\n"
        "<b>Выберите быструю сумму или введите свою:</b>\n"
        "<i>(Поддерживаются: 500к, 1.5м, 250000+100000)</i>",
        reply_markup=quick_amounts_keyboard(QUICK_INCOME_AMOUNTS, callback_prefix="inc_quick"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(IncomeStates.enter_amount, F.data.startswith("inc_quick:"))
async def income_quick_amount_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 2b: Quick amount chip clicked."""
    amount_str = callback.data.split(":")[1]
    amount = Decimal(amount_str)

    await state.update_data(amount=str(amount))
    await state.set_state(IncomeStates.enter_comment)

    await callback.message.edit_text(
        f"Сумма: <b>+{format_amount(amount)} сум</b>\n\n"
        "💬 <b>Добавьте комментарий</b> (за что доход, проект, клиент и т.д.):\n"
        "<i>Или нажмите «Пропустить ➡️»</i>",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(IncomeStates.enter_amount)
async def income_amount_entered(
    message: Message, state: FSMContext
) -> None:
    """Step 3: Amount received via text input (using smart parser)."""
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(
            "⚠️ Пожалуйста, введите корректную сумму цифрами.\n"
            "<i>(Например: 500000, 500к, 1.5м или 250k+150k)</i>",
            reply_markup=quick_amounts_keyboard(QUICK_INCOME_AMOUNTS, callback_prefix="inc_quick"),
            parse_mode="HTML",
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(IncomeStates.enter_comment)

    await message.answer(
        f"Сумма: <b>+{format_amount(amount)} сум</b>\n\n"
        "💬 <b>Добавьте комментарий</b> (за что доход, проект, клиент и т.д.):\n"
        "<i>Или нажмите «Пропустить ➡️»</i>",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(IncomeStates.enter_comment, F.data == "action:skip_comment")
async def income_skip_comment(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4a: Comment skipped."""
    await state.update_data(comment=None)
    await prompt_account_selection(callback.message, session, state, is_callback=True)
    await callback.answer()


@router.message(IncomeStates.enter_comment)
async def income_comment_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 4b: Comment entered."""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await prompt_account_selection(message, session, state, is_callback=False)


async def prompt_account_selection(
    message_or_msg, session: AsyncSession, state: FSMContext, is_callback: bool
) -> None:
    """Show account selection for income."""
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
        f"Сумма: <b>+{format_amount(amount)} сум</b>{comment_line}\n"
        "Куда поступили деньги?"
    )

    await state.set_state(IncomeStates.select_account)
    if is_callback:
        await message_or_msg.edit_text(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="inc_acc"),
            parse_mode="HTML",
        )
    else:
        await message_or_msg.answer(
            text,
            reply_markup=accounts_keyboard(accounts, callback_prefix="inc_acc"),
            parse_mode="HTML",
        )


@router.callback_query(IncomeStates.select_account, F.data.startswith("inc_acc:"))
async def income_account_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 5: Account selected, ask what percentage to put into savings."""
    account_id = int(callback.data.split(":")[1])
    await state.update_data(account_id=account_id)

    data = await state.get_data()
    amount = Decimal(data["amount"])

    await state.set_state(IncomeStates.select_savings_percent)
    await callback.message.edit_text(
        f"💰 Доход: <b>+{format_amount(amount)} сум</b>\n\n"
        "💵 <b>Сколько процентов отложить в накопления?</b>\n"
        "<i>Выберите процент с подсказкой суммы:</i>",
        reply_markup=income_savings_percent_keyboard(amount),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(IncomeStates.select_savings_percent, F.data.startswith("inc_sav:"))
async def income_savings_percent_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Step 6: Percent selected, finalize income and savings deposit."""
    percent = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    total_amount = Decimal(data["amount"])
    category_id = data.get("category_id")
    cat_icon = data.get("category_icon", "💰")
    cat_name = data.get("category_name", "Доход")
    comment = data.get("comment")
    account_id = data["account_id"]

    finance_service = FinanceService(session)
    savings_service = SavingsService(session)

    try:
        tx, account = await finance_service.add_income(
            user_id=user.id,
            account_id=account_id,
            category_id=category_id,
            amount=total_amount,
            description=comment,
        )

        savings_deposited = Decimal("0")
        savings_account = None
        newly_reached_goals = []
        if percent > 0:
            savings_deposited = (total_amount * Decimal(percent) / Decimal(100)).quantize(Decimal("1"))
            if savings_deposited > Decimal("0"):
                saving_desc = f"Отчисление {percent}% с дохода ({cat_name})"
                if comment:
                    saving_desc += f": {comment}"
                _, account, savings_account, newly_reached_goals = await savings_service.deposit(
                    user_id=user.id,
                    source_account_id=account_id,
                    amount=savings_deposited,
                    description=saving_desc,
                )
    except Exception as e:
        logger.error("Error adding income: %s", e, exc_info=True)
        await callback.message.edit_text(
            f"⚠️ Ошибка: {e}",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    lines = [
        "✅ <b>Доход успешно добавлен</b>\n",
        f"{cat_icon} {cat_name}",
        f"<b>+{format_amount(total_amount)} сум</b>",
    ]
    if comment:
        lines.append(f"📝 <i>«{comment}»</i>")

    lines.append(f"\n{account.icon} <b>{account.name}</b> (баланс: {format_amount(account.balance)} сум)")

    if percent > 0 and savings_account:
        lines.append(
            f"\n💵 <b>Отложено в накопления ({percent}%):</b> +{format_amount(savings_deposited)} сум\n"
            f"Всего в накоплениях: <b>{format_amount(savings_account.balance)} сум</b>"
        )

    if newly_reached_goals:
        lines.append("\n━━━━━━━━━━━━")
        for g in newly_reached_goals:
            lines.append(f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> Вы накопили достаточно средств для цели:\n🎯 <b>«{g.name}»</b> ({format_amount(g.target_amount)} сум)!")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tx_success_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()
