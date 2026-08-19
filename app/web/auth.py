"""Telegram Mini App authentication and initData validation."""

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl, unquote
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """Validate Telegram WebApp initData string using Telegram's HMAC-SHA256 algorithm.
    
    Returns the parsed user dict if valid, else None.
    """
    if not init_data:
        return None

    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")

        # Construct data_check_string: sorted alphabetically, key=value joined by \n
        data_check_list = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = "\n".join(data_check_list)

        # Telegram secret key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("Telegram WebApp initData hash mismatch")
            return None

        user_raw = parsed_data.get("user")
        if user_raw:
            return json.loads(user_raw)
        return None

    except Exception as e:
        logger.warning("Failed to validate Telegram initData: %s", e)
        return None


def get_authenticated_user_id(
    init_data: str | None,
    profile_id_header: str | int | None = None,
) -> tuple[int | None, str | None, int | None]:
    """Extract authenticated telegram_id and name, or explicit user_id.
    
    Returns (telegram_id, full_name, explicit_user_id)
    """
    explicit_user_id = None
    if profile_id_header:
        try:
            explicit_user_id = int(profile_id_header)
        except (ValueError, TypeError):
            pass

    if init_data:
        user_info = validate_telegram_init_data(init_data, settings.bot_token)
        if user_info and "id" in user_info:
            tg_id = int(user_info["id"])
            first_name = user_info.get("first_name", "")
            last_name = user_info.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() or f"User {tg_id}"
            return tg_id, full_name, explicit_user_id

    if explicit_user_id:
        return None, None, explicit_user_id

    # Development / Single-user fallback
    return settings.admin_user_id, "Admin User", None
