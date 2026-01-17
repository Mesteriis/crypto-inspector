from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here for Alembic to detect them
from db.models.candlestick import CandlestickRecord  # noqa: E402, F401
