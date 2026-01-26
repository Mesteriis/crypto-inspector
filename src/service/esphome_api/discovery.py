"""mDNS/Zeroconf service discovery for ESPHome API.

Announces the service as ESPHome-compatible device.
"""

from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Try to import zeroconf
try:
    from zeroconf import IPVersion, ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf

    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("zeroconf not available, mDNS discovery disabled")

# ESPHome service type
ESPHOME_SERVICE_TYPE = "_esphomelib._tcp.local."


def get_local_ip() -> str:
    """Get local IP address."""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ESPHomeDiscovery:
    """mDNS service discovery for ESPHome API."""

    def __init__(
        self,
        name: str = "crypto_inspect",
        port: int = 6053,
        mac_address: str = "AA:BB:CC:DD:EE:FF",
    ) -> None:
        """Initialize discovery."""
        self.name = name
        self.port = port
        self.mac_address = mac_address
        self._zeroconf: AsyncZeroconf | None = None
        self._service_info: ServiceInfo | None = None

    async def start(self) -> bool:
        """Start mDNS service announcement."""
        if not ZEROCONF_AVAILABLE:
            logger.warning("Zeroconf not available, skipping mDNS")
            return False

        try:
            local_ip = get_local_ip()
            logger.info("ESPHome Discovery: Local IP is %s", local_ip)

            # Create service info
            # ESPHome uses: name._esphomelib._tcp.local.
            self._service_info = ServiceInfo(
                type_=ESPHOME_SERVICE_TYPE,
                name=f"{self.name}.{ESPHOME_SERVICE_TYPE}",
                port=self.port,
                properties={
                    "mac": self.mac_address,
                    "version": "1.0.0",
                    "platform": "ESP32",
                    "board": "virtual",
                    "network": "ethernet",
                },
                server=f"{self.name}.local.",
                addresses=[socket.inet_aton(local_ip)],
            )

            # Start zeroconf
            self._zeroconf = AsyncZeroconf(ip_version=IPVersion.V4Only)
            await self._zeroconf.async_register_service(self._service_info)

            logger.info(
                "ESPHome Discovery: Registered as %s on port %d",
                self.name,
                self.port,
            )
            return True

        except Exception as e:
            logger.error("ESPHome Discovery: Failed to start: %s", e)
            return False

    async def stop(self) -> None:
        """Stop mDNS service."""
        if self._zeroconf and self._service_info:
            try:
                await self._zeroconf.async_unregister_service(
                    self._service_info
                )
                await self._zeroconf.async_close()
            except Exception as e:
                logger.error("ESPHome Discovery: Failed to stop: %s", e)
            finally:
                self._zeroconf = None
                self._service_info = None

        logger.info("ESPHome Discovery: Stopped")


# Global discovery instance
_discovery: ESPHomeDiscovery | None = None


def get_esphome_discovery() -> ESPHomeDiscovery:
    """Get or create global discovery instance."""
    global _discovery
    if _discovery is None:
        _discovery = ESPHomeDiscovery()
    return _discovery


async def start_esphome_discovery() -> bool:
    """Start global ESPHome discovery."""
    discovery = get_esphome_discovery()
    return await discovery.start()


async def stop_esphome_discovery() -> None:
    """Stop global ESPHome discovery."""
    global _discovery
    if _discovery:
        await _discovery.stop()
        _discovery = None
