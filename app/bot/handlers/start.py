"""Start command and main menu handler with real-time financial mini-dashboard."""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import main_menu_keyboard, format_amount
from app.services.account_service import AccountService
from app.services.savings_service import SavingsService
from app.services.user_service import ensure_user_exists

router = Router(name="start")
logger = logging.getLogger(__name__)


async def get_main_menu_text(user_id: int, session: AsyncSession) -> str:
    """Generate dynamic main menu header with real-time balance summary."""
    acc_service = AccountService(session)
    sav_service = SavingsService(session)

    summary = await acc_service.get_bank_summary(user_id)
    goals_overview = await sav_service.get_multi_goals_overview(user_id)

    available = summary["available_funds"]
    savings = summary["savings_balance"]
    capital = summary["total_capital"]
    projections = summary.get("projections", {})
    usd_val = projections.get("USD")
    usd_str = f" <i>(≈ ${usd_val:,.2f})</i>" if usd_val else ""

    goal_extra = ""
    if goals_overview["has_goals"]:
        goal_extra = f" <i>(🎯 цели: {goals_overview['overall_pct']}%)</i>"

    lines = [
        "💰 <b>Hisoblash Bot</b>\n",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💳 <b>Доступно:</b>  {format_amount(available)} сум",
        f"💵 <b>Накоплено:</b> {format_amount(savings)} сум{goal_extra}",
        f"💰 <b>Капитал:</b>    {format_amount(capital)} сум{usd_str}",
        "━━━━━━━━━━━━━━━━━━━━\n",
        "Выберите действие:",
    ]
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Handle /start command — show main menu with mini-dashboard."""
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )

    logger.info("User started bot: telegram_id=%d", message.from_user.id)
    text = await get_main_menu_text(user.id, session)

    await message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:main")
async def callback_main_menu(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Return to main menu from any screen."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    text = await get_main_menu_text(user.id, session)

    await callback.message.edit_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "action:cancel")
async def callback_cancel(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Cancel any multi-step operation and return to main menu."""
    await state.clear()
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    text = "❌ <i>Операция отменена.</i>\n\n" + await get_main_menu_text(user.id, session)

    await callback.message.edit_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
