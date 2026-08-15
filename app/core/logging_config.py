"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path


def setup_logging(log_level: str, logs_dir: Path) -> None:
    """Configure application logging.

    Logs go to both console (stdout) and a file in the logs directory.
    Sensitive data (BOT_TOKEN, passwords) must never be logged.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        logs_dir: Directory to store log files.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(
        logs_dir / "bot.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(file_handler)

    # Quiet noisy libraries
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Logging initialized (level=%s)", log_level)
