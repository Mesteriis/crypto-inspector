"""add traditional_asset_records table

Revision ID: 932064f532ad
Revises: 7c7ba6464e14
Create Date: 2026-01-18 02:47:37.384464

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '932064f532ad'
down_revision: str | None = '7c7ba6464e14'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "traditional_asset_records",
        sa.Column(
            "asset_type",
            sa.String(length=50),
            nullable=False,
            comment="Asset type: forex, index, commodity, metal",
        ),
        sa.Column(
            "symbol",
            sa.String(length=50),
            nullable=False,
            comment="Asset symbol (e.g., GOLD, SP500, EUR_USD, OIL_BRENT)",
        ),
        sa.Column(
            "timestamp",
            sa.BigInteger(),
            nullable=False,
            comment="Record timestamp as Unix timestamp in milliseconds",
        ),
        sa.Column(
            "open_price",
            sa.Numeric(precision=20, scale=6),
            nullable=True,
            comment="Opening price",
        ),
        sa.Column(
            "high_price",
            sa.Numeric(precision=20, scale=6),
            nullable=True,
            comment="Highest price",
        ),
        sa.Column(
            "low_price",
            sa.Numeric(precision=20, scale=6),
            nullable=True,
            comment="Lowest price",
        ),
        sa.Column(
            "close_price",
            sa.Numeric(precision=20, scale=6),
            nullable=False,
            comment="Closing/current price",
        ),
        sa.Column(
            "volume",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="Trading volume (if available)",
        ),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when record was loaded",
        ),
        sa.PrimaryKeyConstraint("symbol", "timestamp"),
        comment="Stores traditional finance data: forex, indices, commodities",
    )
    op.create_index(
        "ix_traditional_asset_type",
        "traditional_asset_records",
        ["asset_type"],
        unique=False,
    )
    op.create_index(
        "ix_traditional_symbol",
        "traditional_asset_records",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_traditional_timestamp",
        "traditional_asset_records",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_traditional_loaded_at",
        "traditional_asset_records",
        ["loaded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_traditional_loaded_at", table_name="traditional_asset_records")
    op.drop_index("ix_traditional_timestamp", table_name="traditional_asset_records")
    op.drop_index("ix_traditional_symbol", table_name="traditional_asset_records")
    op.drop_index("ix_traditional_asset_type", table_name="traditional_asset_records")
    op.drop_table("traditional_asset_records")
