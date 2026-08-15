"""Settings handler — account management, backup, and preferences."""

from decimal import Decimal
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.backup import create_backup
from app.bot.keyboards.inline import (
    settings_menu_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    format_amount,
)
from app.bot.states.states import AccountStates
from app.services.account_service import AccountService
from app.services.user_service import ensure_user_exists

router = Router(name="settings")
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:settings")
async def show_settings_menu(
    callback: CallbackQuery,
) -> None:
    """Show settings menu."""
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел:",
        reply_markup=settings_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:backup")
async def handle_backup_request(
    callback: CallbackQuery,
) -> None:
    """Create database backup on demand."""
    try:
        backup_path = create_backup()
        await callback.message.edit_text(
            f"✅ <b>Резервная копия создана!</b>\n\nФайл: <code>{backup_path.name}</code>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ Ошибка создания бэкапа: {e}",
            reply_markup=back_to_menu_keyboard(),
        )
    await callback.answer()


# ─── ADD ACCOUNT FLOW ─────────────────────────

@router.callback_query(F.data == "settings:add_account")
async def start_add_account(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Step 1: Ask account name."""
    await state.set_state(AccountStates.enter_name)
    await callback.message.edit_text(
        "💳 <b>Добавить новый счет</b>\n\nВведите название счета:\n<i>(Например: Humo, Uzcard, Visa, Сейф)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AccountStates.enter_name)
async def account_name_entered(
    message: Message, state: FSMContext
) -> None:
    """Step 2: Ask initial balance."""
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Введите название счета:")
        return

    await state.update_data(account_name=name)
    await state.set_state(AccountStates.enter_initial_balance)

    await message.answer(
        f"Название: <b>{name}</b>\n\nВведите начальный баланс счета:\n<i>(Если 0, просто напишите 0)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(AccountStates.enter_initial_balance)
async def account_initial_balance_entered(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Step 3: Create account."""
    text = message.text.replace(" ", "").replace(",", ".").strip()
    try:
        balance = Decimal(text)
        if balance < 0:
            raise ValueError
    except Exception:
        await message.answer(
            "⚠️ Введите корректное положительное число или 0:",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    await state.clear()

    user = await ensure_user_exists(
        session=session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )

    name = data["account_name"]
    acc_service = AccountService(session)
    account = await acc_service.create_account(
        user_id=user.id,
        name=name,
        icon="💳",
        initial_balance=balance,
    )

    await message.answer(
        f"✅ <b>Счет успешно добавлен!</b>\n\n"
        f"{account.icon} {account.name}\n"
        f"Баланс: <b>{format_amount(account.balance)} сум</b>",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
