"""Backup utility: python -m app.backup

Creates a timestamped copy of the SQLite database in the backups/ directory.
"""

import shutil
from datetime import datetime
from pathlib import Path

from app.core.config import settings


def create_backup() -> Path:
    """Create a timestamped backup of the database file.

    Returns:
        Path to the created backup file.
    """
    # Parse the database file path from DATABASE_URL
    # Format: sqlite+aiosqlite:///./data/finance.db
    db_url = settings.database_url
    if ":///" in db_url:
        db_path_str = db_url.split("///", 1)[1]
    else:
        db_path_str = db_url.split("//", 1)[1]

    db_path = Path(db_path_str)
    if not db_path.is_absolute():
        db_path = settings.base_dir / db_path

    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        raise SystemExit(1)

    # Create backups directory
    backup_dir = settings.backups_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"finance_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    print(f"   Size: {backup_path.stat().st_size / 1024:.1f} KB")

    return backup_path


if __name__ == "__main__":
    create_backup()
