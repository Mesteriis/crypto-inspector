"""
CSV Export Service.

Export trading data to CSV format:
- Trade history
- P&L summary by asset
- Tax-compatible format

Форматы экспорта:
- trades: История сделок
- pnl: Сводка P&L по активам
- tax: Формат для налоговой отчетности
"""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from services.exchange.bybit_portfolio import BybitPortfolio, PnlPeriod, get_bybit_portfolio

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Export format types."""

    TRADES = "trades"
    PNL = "pnl"
    TAX = "tax"


@dataclass
class ExportResult:
    """Export result with CSV content."""

    format: ExportFormat
    filename: str
    content: str
    rows_count: int
    period_start: datetime | None
    period_end: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format.value,
            "filename": self.filename,
            "rows_count": self.rows_count,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


class CSVExporter:
    """
    CSV export service for trading data.

    Supports multiple export formats compatible with
    tax software and spreadsheet applications.
    """

    def __init__(self, portfolio: BybitPortfolio | None = None):
        self._portfolio = portfolio or get_bybit_portfolio()

    async def export_trades(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        symbol: str | None = None,
    ) -> ExportResult:
        """
        Export trade history to CSV.

        Args:
            start_time: Start of period
            end_time: End of period
            symbol: Optional symbol filter

        Returns:
            ExportResult with CSV content
        """
        trades = await self._portfolio.get_trades(
            start_time=start_time,
            end_time=end_time,
            symbol=symbol,
            limit=100,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Дата",
                "Время",
                "Символ",
                "Сторона",
                "Цена",
                "Количество",
                "Объем (USDT)",
                "Комиссия",
                "Валюта комиссии",
                "Реализованный P&L",
                "Тип",
                "ID Сделки",
                "ID Ордера",
            ]
        )

        # Data rows
        for trade in trades:
            writer.writerow(
                [
                    trade.exec_time.strftime("%Y-%m-%d"),
                    trade.exec_time.strftime("%H:%M:%S"),
                    trade.symbol,
                    trade.side,
                    round(trade.price, 2),
                    round(trade.qty, 8),
                    round(trade.value, 2),
                    round(trade.fee, 8),
                    trade.fee_currency,
                    round(trade.realized_pnl, 2),
                    "Maker" if trade.is_maker else "Taker",
                    trade.trade_id,
                    trade.order_id,
                ]
            )

        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_str = f"_{symbol}" if symbol else ""
        filename = f"bybit_trades{symbol_str}_{date_str}.csv"

        return ExportResult(
            format=ExportFormat.TRADES,
            filename=filename,
            content=output.getvalue(),
            rows_count=len(trades),
            period_start=start_time,
            period_end=end_time,
        )

    async def export_pnl_summary(
        self,
        period: PnlPeriod = PnlPeriod.MONTH,
    ) -> ExportResult:
        """
        Export P&L summary by asset to CSV.

        Args:
            period: Time period for P&L calculation

        Returns:
            ExportResult with CSV content
        """
        pnl = await self._portfolio.calculate_pnl(period)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Период",
                "Символ",
                "Реализованный P&L (USDT)",
            ]
        )

        # Summary row
        writer.writerow(
            [
                period.name_ru,
                "ИТОГО",
                round(pnl.realized_pnl, 2),
            ]
        )

        # By symbol
        for symbol, sym_pnl in sorted(pnl.by_symbol.items(), key=lambda x: x[1], reverse=True):
            writer.writerow(
                [
                    period.name_ru,
                    symbol,
                    round(sym_pnl, 2),
                ]
            )

        # Stats
        writer.writerow([])
        writer.writerow(["Статистика"])
        writer.writerow(["Всего сделок", pnl.trades_count])
        writer.writerow(["Прибыльных", pnl.win_count])
        writer.writerow(["Убыточных", pnl.loss_count])
        writer.writerow(["Win Rate", f"{pnl.win_rate:.1f}%"])
        writer.writerow(["Комиссии уплачено", round(pnl.fees_paid, 2)])
        writer.writerow(["Нереализованный P&L", round(pnl.unrealized_pnl, 2)])

        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bybit_pnl_{period.value}_{date_str}.csv"

        return ExportResult(
            format=ExportFormat.PNL,
            filename=filename,
            content=output.getvalue(),
            rows_count=len(pnl.by_symbol) + 1,
            period_start=pnl.start_time,
            period_end=pnl.end_time,
        )

    async def export_tax_report(
        self,
        year: int | None = None,
    ) -> ExportResult:
        """
        Export tax-compatible report.

        Format compatible with tax reporting requirements.

        Args:
            year: Tax year (default: current year)

        Returns:
            ExportResult with CSV content
        """
        if year is None:
            year = datetime.now().year

        start_time = datetime(year, 1, 1)
        end_time = datetime(year, 12, 31, 23, 59, 59)

        # Get all trades for the year
        trades = await self._portfolio.get_trades(
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header - tax report format
        writer.writerow(
            [
                "Date",
                "Time",
                "Asset",
                "Type",  # Buy/Sell
                "Amount",
                "Price (USD)",
                "Value (USD)",
                "Fee (USD)",
                "Realized Gain/Loss (USD)",
                "Exchange",
                "Transaction ID",
            ]
        )

        total_gains = 0
        total_losses = 0
        total_fees = 0

        for trade in trades:
            value_usd = trade.value
            fee_usd = trade.fee

            writer.writerow(
                [
                    trade.exec_time.strftime("%Y-%m-%d"),
                    trade.exec_time.strftime("%H:%M:%S"),
                    trade.symbol.replace("USDT", ""),  # Remove USDT suffix
                    trade.side,
                    round(trade.qty, 8),
                    round(trade.price, 2),
                    round(value_usd, 2),
                    round(fee_usd, 4),
                    round(trade.realized_pnl, 2),
                    "Bybit",
                    trade.trade_id,
                ]
            )

            if trade.realized_pnl > 0:
                total_gains += trade.realized_pnl
            else:
                total_losses += abs(trade.realized_pnl)
            total_fees += fee_usd

        # Summary section
        writer.writerow([])
        writer.writerow([f"Tax Year {year} Summary"])
        writer.writerow(["Total Transactions", len(trades)])
        writer.writerow(["Total Capital Gains", round(total_gains, 2)])
        writer.writerow(["Total Capital Losses", round(total_losses, 2)])
        writer.writerow(["Net Gain/Loss", round(total_gains - total_losses, 2)])
        writer.writerow(["Total Fees Paid", round(total_fees, 2)])
        writer.writerow([])
        writer.writerow(["Note: This report is for informational purposes only."])
        writer.writerow(["Please consult a tax professional for accurate tax reporting."])

        filename = f"bybit_tax_report_{year}.csv"

        return ExportResult(
            format=ExportFormat.TAX,
            filename=filename,
            content=output.getvalue(),
            rows_count=len(trades),
            period_start=start_time,
            period_end=end_time,
        )

    async def export_positions(self) -> ExportResult:
        """
        Export current open positions to CSV.

        Returns:
            ExportResult with CSV content
        """
        positions = await self._portfolio.get_positions()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Символ",
                "Сторона",
                "Размер",
                "Цена входа",
                "Текущая цена",
                "Плечо",
                "Стоимость позиции (USDT)",
                "Нереализованный P&L (USDT)",
                "P&L %",
                "Цена ликвидации",
                "Take Profit",
                "Stop Loss",
            ]
        )

        total_value = 0
        total_pnl = 0

        for pos in positions:
            pnl_pct = (pos.unrealized_pnl / pos.position_value * 100) if pos.position_value > 0 else 0

            writer.writerow(
                [
                    pos.symbol,
                    pos.side,
                    round(pos.size, 8),
                    round(pos.entry_price, 2),
                    round(pos.mark_price, 2),
                    f"{pos.leverage}x",
                    round(pos.position_value, 2),
                    round(pos.unrealized_pnl, 2),
                    f"{pnl_pct:.2f}%",
                    round(pos.liq_price, 2) if pos.liq_price else "N/A",
                    round(pos.take_profit, 2) if pos.take_profit else "N/A",
                    round(pos.stop_loss, 2) if pos.stop_loss else "N/A",
                ]
            )

            total_value += pos.position_value
            total_pnl += pos.unrealized_pnl

        # Summary
        writer.writerow([])
        writer.writerow(["ИТОГО", "", "", "", "", "", round(total_value, 2), round(total_pnl, 2)])

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bybit_positions_{date_str}.csv"

        return ExportResult(
            format=ExportFormat.TRADES,  # Reuse format
            filename=filename,
            content=output.getvalue(),
            rows_count=len(positions),
            period_start=None,
            period_end=None,
        )


# Global instance
_csv_exporter: CSVExporter | None = None


def get_csv_exporter() -> CSVExporter:
    """Get global CSV exporter instance."""
    global _csv_exporter
    if _csv_exporter is None:
        _csv_exporter = CSVExporter()
    return _csv_exporter
