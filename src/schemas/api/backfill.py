"""Backfill API schemas."""

from pydantic import BaseModel


class TriggerBackfillRequest(BaseModel):
    """Request to trigger backfill."""

    crypto_symbols: list[str] | None = None
    crypto_intervals: list[str] | None = None
    crypto_years: int | None = None
    traditional_symbols: list[str] | None = None
    traditional_years: int | None = None
    force: bool = False
