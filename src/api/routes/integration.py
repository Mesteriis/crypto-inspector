"""API routes for Home Assistant custom integration.

Provides endpoints for the custom_components/crypto_inspect integration
to fetch sensor data and registry information.
"""

import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import APP_VERSION
from models.repositories.sensor_state import SensorStateRepository
from models.session import get_db
from service.ha.core.registry import SensorRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integration", tags=["integration"])


@router.get("/sensors")
async def get_all_sensor_values(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all sensor values for Home Assistant integration.

    Returns all persisted sensor states from database in a flat format
    suitable for the custom integration coordinator.

    Returns:
        Dict with sensors data and metadata
    """
    repo = SensorStateRepository(session)
    states = await repo.get_all()

    sensors: dict[str, Any] = {}

    for state in states:
        # Extract sensor_id from unique_id (crypto_inspect_<sensor_id>)
        sensor_id = state.name

        # Parse JSON value if stored as JSON
        try:
            value = json.loads(state.value)
        except (json.JSONDecodeError, TypeError):
            value = state.value

        sensors[sensor_id] = {
            "value": value,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }

    return {
        "sensors": sensors,
        "count": len(sensors),
        "version": APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/registry")
async def get_sensor_registry() -> dict[str, Any]:
    """
    Get sensor registry (metadata) for Home Assistant integration.

    Returns sensor definitions including names, icons, units, and types
    for all registered sensors.

    Returns:
        Dict with sensor metadata
    """
    SensorRegistry.ensure_initialized()

    sensors: dict[str, dict[str, Any]] = {}

    for sensor_id, sensor_class in SensorRegistry.get_all().items():
        config = sensor_class.config
        sensors[sensor_id] = {
            "name": config.name,
            "name_ru": config.name_ru,
            "icon": config.icon,
            "unit": config.unit,
            "device_class": config.device_class,
            "entity_category": config.entity_category,
            "description": config.description,
            "description_ru": config.description_ru,
            "value_type": config.value_type,
        }

    categories = {
        cat: SensorRegistry.get_by_category(cat)
        for cat in SensorRegistry.get_categories()
    }

    return {
        "sensors": sensors,
        "categories": categories,
        "count": len(sensors),
        "version": APP_VERSION,
    }


@router.get("/status")
async def get_integration_status(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get integration status for diagnostics.

    Returns:
        Dict with status information
    """
    SensorRegistry.ensure_initialized()

    repo = SensorStateRepository(session)
    states = await repo.get_all()

    # Get latest update time
    latest_update = None
    for state in states:
        if state.updated_at:
            if latest_update is None or state.updated_at > latest_update:
                latest_update = state.updated_at

    return {
        "status": "online",
        "version": APP_VERSION,
        "sensors_registered": SensorRegistry.count(),
        "sensors_with_data": len(states),
        "categories": SensorRegistry.get_categories(),
        "latest_update": latest_update.isoformat() if latest_update else None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/download")
async def download_integration() -> StreamingResponse:
    """
    Download custom_components/crypto_inspect as a ZIP file.

    Users can extract this to their Home Assistant config directory
    to install the integration.

    Returns:
        ZIP file containing the custom_component
    """
    # Try multiple possible locations for custom_components
    possible_paths = [
        Path("/custom_components/crypto_inspect"),  # Docker container
        Path("/app/custom_components/crypto_inspect"),  # Alternative Docker path
        Path(__file__).parent.parent.parent.parent.parent / "custom_components" / "crypto_inspect",  # Development
    ]

    component_path = None
    for path in possible_paths:
        if path.exists():
            component_path = path
            break

    if not component_path:
        return StreamingResponse(
            iter([b'{"error": "Integration files not found"}']),
            media_type="application/json",
            status_code=404,
        )

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in component_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                # Preserve directory structure: custom_components/crypto_inspect/...
                arcname = f"custom_components/crypto_inspect/{file_path.relative_to(component_path)}"
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=crypto_inspect_integration_v{APP_VERSION}.zip"
        },
    )


@router.get("/install-instructions")
async def get_install_instructions() -> dict[str, Any]:
    """
    Get installation instructions for the custom integration.

    Returns:
        Dict with installation steps in EN and RU
    """
    return {
        "version": APP_VERSION,
        "instructions": {
            "en": [
                "1. Download the integration ZIP from /api/integration/download",
                "2. Extract the ZIP to your Home Assistant config directory",
                "3. Restart Home Assistant",
                "4. Go to Settings -> Devices & Services -> Add Integration",
                "5. Search for 'Crypto Inspect' and follow the setup wizard",
                "6. Enter the addon host (usually 'localhost') and port (9999)",
            ],
            "ru": [
                "1. Скачайте ZIP интеграции по адресу /api/integration/download",
                "2. Распакуйте ZIP в директорию config Home Assistant",
                "3. Перезапустите Home Assistant",
                "4. Перейдите в Настройки -> Устройства и службы -> Добавить интеграцию",
                "5. Найдите 'Crypto Inspect' и следуйте мастеру настройки",
                "6. Укажите хост аддона (обычно 'localhost') и порт (9999)",
            ],
        },
        "manual_config": {
            "description": "Alternative: Add to configuration.yaml",
            "yaml": """
# Add to configuration.yaml if config_flow doesn't work
crypto_inspect:
  host: localhost
  port: 9999
  language: ru  # or 'en'
""",
        },
    }
