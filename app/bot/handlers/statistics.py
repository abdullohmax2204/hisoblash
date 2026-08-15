"""Statistics handler — periodic financial reports."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    statistics_period_keyboard,
    back_to_menu_keyboard,
    format_amount,
)
from app.services.statistics_service import StatisticsService
from app.services.user_service import ensure_user_exists

router = Router(name="statistics")
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:statistics")
async def show_statistics_menu(
    callback: CallbackQuery,
) -> None:
    """Show statistics period picker."""
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\nВыберите период:",
        reply_markup=statistics_period_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def show_period_statistics(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Display financial stats for chosen period."""
    period = callback.data.split(":")[1]
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    stats_service = StatisticsService(session)
    data = await stats_service.get_period_stats(user.id, period)

    lines = [f"📊 <b>{data['title']}</b>\n"]
    lines.append(f"💰 <b>Доходы:</b>\n+{format_amount(data['total_income'])} сум\n")
    lines.append(f"💸 <b>Расходы:</b>\n-{format_amount(data['total_expense'])} сум\n")

    if data["total_savings"] > 0:
        lines.append(f"💵 <b>В накопления:</b>\n{format_amount(data['total_savings'])} сум\n")
    if data["total_debt_given"] > 0:
        lines.append(f"🤝 <b>Выдано в долг:</b>\n{format_amount(data['total_debt_given'])} сум\n")

    lines.append("━━━━━━━━━━━━\n")
    sign = "+" if data["net_income"] >= 0 else "-"
    lines.append(f"📈 <b>Доходы − расходы:</b>\n<b>{sign}{format_amount(abs(data['net_income']))} сум</b>")

    if data["top_categories"]:
        lines.append("\n<b>Топ расходов:</b>")
        for cat_name, cat_icon, cat_sum in data["top_categories"]:
            lines.append(f"{cat_icon} {cat_name}: {format_amount(cat_sum)} сум")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=statistics_period_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
