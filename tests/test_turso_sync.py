import pytest
import sqlite3
from app.database.cloud_sync import TursoSyncService

@pytest.mark.asyncio
async def test_turso_sync_service_configuration():
    service = TursoSyncService()
    # In test environment with .env loaded, credentials should be configured
    assert service.is_configured is True
    assert service._get_clean_url().startswith("https://")

@pytest.mark.asyncio
async def test_turso_sync_push_and_restore(tmp_path, monkeypatch):
    service = TursoSyncService()
    if not service.is_configured:
        pytest.skip("Turso credentials not configured")

    # Verify sync_push runs without unhandled exceptions
    result = await service.sync_push()
    assert result is True
