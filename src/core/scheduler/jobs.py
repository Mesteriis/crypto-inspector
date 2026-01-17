"""
Scheduled jobs for the application.

This module contains all scheduled job functions that are registered
with the APScheduler.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def hello_world_job() -> None:
    """
    Test job that prints 'Hello World' to the console.

    This job is scheduled to run every 5 minutes at exact intervals
    (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 minutes).
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{current_time}] Hello World! (Scheduled job executed)"

    # Print to console
    print(message)

    # Also log it
    logger.info(message)
