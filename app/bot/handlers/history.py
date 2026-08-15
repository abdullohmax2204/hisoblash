"""History handler — view grouped transaction history, transaction details, and undo/delete."""

from datetime import datetime, date
from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    history_list_keyboard,
    transaction_detail_keyboard,
    back_to_menu_keyboard,
    format_amount,
)
from app.database.models.transaction import TransactionType
from app.services.finance_service import FinanceService
from app.services.history_service import HistoryService
from app.services.user_service import ensure_user_exists

router = Router(name="history")
logger = logging.getLogger(__name__)

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


def format_date_header(dt: datetime) -> str:
    """Format date into human-readable section header (e.g. 📅 СЕГОДНЯ, 14 АВГУСТА)."""
    today = date.today()
    tx_date = dt.date()

    if tx_date == today:
        return f"📅 <b>СЕГОДНЯ</b>, {dt.day} {MONTHS_RU[dt.month]}"
    elif (today - tx_date).days == 1:
        return f"📅 <b>ВЧЕРА</b>, {dt.day} {MONTHS_RU[dt.month]}"
    else:
        return f"📅 <b>{dt.day} {MONTHS_RU[dt.month]} {dt.year}</b>"


@router.callback_query(F.data == "menu:history")
async def show_history_first_page(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show page 0 of history."""
    await render_history_page(callback, session, page=0)


@router.callback_query(F.data.startswith("history:page:"))
async def change_history_page(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show requested page of history."""
    page = int(callback.data.split(":")[2])
    await render_history_page(callback, session, page=page)


async def render_history_page(callback: CallbackQuery, session: AsyncSession, page: int) -> None:
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )
    hist_service = HistoryService(session)
    transactions, has_more = await hist_service.get_history(user.id, page=page, page_size=6)

    if not transactions and page == 0:
        await callback.message.edit_text(
            "📜 <b>История операций</b>\n\nУ вас пока нет записанных операций.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Build grouped overview text
    lines = [f"📜 <b>История операций</b> (Стр. {page + 1}):\n"]
    current_date_header = None

    for tx in transactions:
        header = format_date_header(tx.created_at)
        if header != current_date_header:
            current_date_header = header
            lines.append(f"\n{header}")

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
            name = "В накопления"
        elif tx.type == TransactionType.SAVING_WITHDRAW.value:
            icon = "↩️"
            name = "Из накоплений"
        elif tx.type == TransactionType.TRANSFER.value:
            icon = "🔄"
            name = "Перевод"

        desc_part = f" <i>«{tx.description}»</i>" if tx.description else ""
        lines.append(f"  • {icon} {name}: <b>{sign}{format_amount(tx.amount)}</b>{desc_part}")

    lines.append("\n<i>Нажмите на кнопку ниже для деталей или удаления:</i>")
    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=history_list_keyboard(transactions, page=page, has_more=has_more),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:view:"))
async def view_transaction_detail(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Show details of selected transaction."""
    tx_id = int(callback.data.split(":")[2])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    hist_service = HistoryService(session)
    tx = await hist_service.get_transaction_by_id(tx_id, user.id)

    if not tx:
        await callback.message.edit_text(
            "⚠️ Операция не найдена.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    type_names = {
        TransactionType.INCOME.value: "💰 Доход",
        TransactionType.EXPENSE.value: "💸 Расход",
        TransactionType.TRANSFER.value: "🔄 Перевод между счетами",
        TransactionType.SAVING.value: "💵 В накопления",
        TransactionType.SAVING_WITHDRAW.value: "↩️ Из накоплений",
        TransactionType.DEBT_GIVEN.value: "🤝 Выдача долга",
        TransactionType.DEBT_RETURN.value: "💰 Возврат долга",
    }

    date_str = tx.created_at.strftime("%d.%m.%Y в %H:%M")
    cat_str = f"{tx.category.icon} {tx.category.name}" if tx.category else "—"
    acc_str = f"{tx.account.icon} {tx.account.name}" if tx.account else "—"

    lines = [
        "📜 <b>Детали операции</b>\n",
        f"<b>Тип:</b> {type_names.get(tx.type, tx.type)}",
        f"<b>Сумма:</b> {format_amount(tx.amount)} сум",
        f"<b>Категория:</b> {cat_str}",
        f"<b>Счет:</b> {acc_str}",
        f"<b>Дата:</b> {date_str}",
    ]

    if tx.description:
        lines.append(f"<b>Примечание:</b> <i>{tx.description}</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=transaction_detail_keyboard(tx.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:undo:"))
async def undo_transaction_action(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Instant undo button from confirmation screen."""
    tx_id = int(callback.data.split(":")[2])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    finance_service = FinanceService(session)
    success = await finance_service.delete_transaction(user.id, tx_id)

    if success:
        await callback.message.edit_text(
            "↩️ <b>Операция успешно отменена!</b>\nБалансы всех счетов восстановлены.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "⚠️ Операция не найдена или уже была отменена.",
            reply_markup=back_to_menu_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:delete:"))
async def delete_transaction(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Delete a transaction and restore balance."""
    tx_id = int(callback.data.split(":")[2])
    user = await ensure_user_exists(
        session=session,
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name,
    )

    finance_service = FinanceService(session)
    success = await finance_service.delete_transaction(user.id, tx_id)

    if success:
        await callback.answer("✅ Операция удалена, баланс восстановлен.", show_alert=True)
    else:
        await callback.answer("⚠️ Не удалось удалить операцию.", show_alert=True)

    await render_history_page(callback, session, page=0)
