"""Portfolio API schemas."""

from pydantic import BaseModel


class HoldingRequest(BaseModel):
    """Request to add/update a holding."""

    symbol: str
    amount: float
    avg_price: float
