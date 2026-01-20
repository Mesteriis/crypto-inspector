"""
Signal History Tracking.

Stores and tracks trading signals:
- Record all generated signals
- Track outcomes (price after 24h/7d)
- Calculate win rates and statistics
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Type of trading signal."""

    BUY = "buy"
    SELL = "sell"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    NEUTRAL = "neutral"


class SignalSource(Enum):
    """Source of the signal."""

    DIVERGENCE = "divergence"
    PATTERN = "pattern"
    INDICATOR = "indicator"
    COMPOSITE = "composite"
    INVESTOR = "investor"
    ALERT = "alert"


class SignalOutcome(Enum):
    """Outcome of signal."""

    PENDING = "pending"  # Not enough time passed
    WIN = "win"  # Price moved in predicted direction
    LOSS = "loss"  # Price moved against prediction
    NEUTRAL = "neutral"  # Price stayed flat


@dataclass
class Signal:
    """Single trading signal."""

    id: str
    symbol: str
    signal_type: SignalType
    source: SignalSource
    created_at: datetime
    price_at_signal: float
    confidence: int  # 0-100
    description: str
    description_ru: str

    # Outcome tracking
    outcome_24h: SignalOutcome = SignalOutcome.PENDING
    outcome_7d: SignalOutcome = SignalOutcome.PENDING
    price_after_24h: float | None = None
    price_after_7d: float | None = None
    pnl_24h_pct: float | None = None
    pnl_7d_pct: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "source": self.source.value,
            "created_at": self.created_at.isoformat(),
            "price_at_signal": self.price_at_signal,
            "confidence": self.confidence,
            "description": self.description,
            "description_ru": self.description_ru,
            "outcome_24h": self.outcome_24h.value,
            "outcome_7d": self.outcome_7d.value,
            "price_after_24h": self.price_after_24h,
            "price_after_7d": self.price_after_7d,
            "pnl_24h_pct": round(self.pnl_24h_pct, 2) if self.pnl_24h_pct else None,
            "pnl_7d_pct": round(self.pnl_7d_pct, 2) if self.pnl_7d_pct else None,
            "age_hours": self._get_age_hours(),
        }

    def _get_age_hours(self) -> float:
        """Get signal age in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600

    def update_outcome(self, current_price: float) -> None:
        """Update signal outcome based on current price."""
        age = datetime.now() - self.created_at

        # Update 24h outcome if 24+ hours passed
        if age >= timedelta(hours=24) and self.outcome_24h == SignalOutcome.PENDING:
            self.price_after_24h = current_price
            pnl = ((current_price - self.price_at_signal) / self.price_at_signal) * 100
            self.pnl_24h_pct = pnl

            self.outcome_24h = self._determine_outcome(pnl)

        # Update 7d outcome if 7+ days passed
        if age >= timedelta(days=7) and self.outcome_7d == SignalOutcome.PENDING:
            self.price_after_7d = current_price
            pnl = ((current_price - self.price_at_signal) / self.price_at_signal) * 100
            self.pnl_7d_pct = pnl

            self.outcome_7d = self._determine_outcome(pnl)

    def _determine_outcome(self, pnl_pct: float) -> SignalOutcome:
        """Determine outcome based on P&L and signal type."""
        # For buy signals, positive P&L is win
        if self.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            if pnl_pct >= 2:
                return SignalOutcome.WIN
            if pnl_pct <= -2:
                return SignalOutcome.LOSS
            return SignalOutcome.NEUTRAL

        # For sell signals, negative P&L is win (price went down)
        if self.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            if pnl_pct <= -2:
                return SignalOutcome.WIN
            if pnl_pct >= 2:
                return SignalOutcome.LOSS
            return SignalOutcome.NEUTRAL

        return SignalOutcome.NEUTRAL


@dataclass
class SignalStats:
    """Signal statistics."""

    timestamp: datetime
    total_signals: int
    signals_24h: int
    win_rate_24h: float  # Percentage
    win_rate_7d: float
    avg_pnl_24h: float
    avg_pnl_7d: float
    best_signal: Signal | None = None
    worst_signal: Signal | None = None
    by_source: dict[str, dict] = field(default_factory=dict)
    by_type: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_signals": self.total_signals,
            "signals_24h": self.signals_24h,
            "win_rate_24h": round(self.win_rate_24h, 1),
            "win_rate_7d": round(self.win_rate_7d, 1),
            "avg_pnl_24h": round(self.avg_pnl_24h, 2),
            "avg_pnl_7d": round(self.avg_pnl_7d, 2),
            "best_signal": (
                {
                    "id": self.best_signal.id,
                    "symbol": self.best_signal.symbol,
                    "pnl": self.best_signal.pnl_7d_pct or self.best_signal.pnl_24h_pct,
                }
                if self.best_signal
                else None
            ),
            "worst_signal": (
                {
                    "id": self.worst_signal.id,
                    "symbol": self.worst_signal.symbol,
                    "pnl": self.worst_signal.pnl_7d_pct or self.worst_signal.pnl_24h_pct,
                }
                if self.worst_signal
                else None
            ),
            "by_source": self.by_source,
            "by_type": self.by_type,
            "summary": f"Win rate: {self.win_rate_24h:.0f}% (24h), {self.win_rate_7d:.0f}% (7d)",
            "summary_ru": f"Винрейт: {self.win_rate_24h:.0f}% (24ч), {self.win_rate_7d:.0f}% (7д)",
        }


class SignalHistoryManager:
    """
    Signal history manager.

    Tracks signals and calculates statistics.
    Note: In production, this should persist to database.
    """

    def __init__(self, max_signals: int = 1000):
        self._signals: dict[str, Signal] = {}
        self._max_signals = max_signals
        self._signal_counter = 0

    def record_signal(
        self,
        symbol: str,
        signal_type: SignalType | str,
        source: SignalSource | str,
        price: float,
        confidence: int = 50,
        description: str = "",
        description_ru: str = "",
    ) -> Signal:
        """
        Record a new signal.

        Args:
            symbol: Trading symbol
            signal_type: Type of signal
            source: Source of signal
            price: Price at signal time
            confidence: Signal confidence (0-100)
            description: English description
            description_ru: Russian description

        Returns:
            Created signal
        """
        if isinstance(signal_type, str):
            signal_type = SignalType(signal_type)
        if isinstance(source, str):
            source = SignalSource(source)

        self._signal_counter += 1
        signal_id = f"sig_{self._signal_counter:06d}"

        signal = Signal(
            id=signal_id,
            symbol=symbol.upper(),
            signal_type=signal_type,
            source=source,
            created_at=datetime.now(),
            price_at_signal=price,
            confidence=confidence,
            description=description or f"{signal_type.value} signal for {symbol}",
            description_ru=description_ru or f"Сигнал {signal_type.value} для {symbol}",
        )

        self._signals[signal_id] = signal

        # Cleanup old signals if over limit
        self._cleanup_old_signals()

        logger.info(f"Recorded signal {signal_id}: {symbol} {signal_type.value}")

        return signal

    def get_signal(self, signal_id: str) -> Signal | None:
        """Get signal by ID."""
        return self._signals.get(signal_id)

    def get_signals(
        self,
        symbol: str | None = None,
        source: SignalSource | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Signal]:
        """
        Get signals with optional filtering.

        Args:
            symbol: Filter by symbol
            source: Filter by source
            since: Only signals after this time
            limit: Maximum number of signals

        Returns:
            List of matching signals
        """
        signals = list(self._signals.values())

        if symbol:
            signals = [s for s in signals if s.symbol == symbol.upper()]

        if source:
            signals = [s for s in signals if s.source == source]

        if since:
            signals = [s for s in signals if s.created_at >= since]

        # Sort by creation time (newest first)
        signals.sort(key=lambda x: x.created_at, reverse=True)

        return signals[:limit]

    def update_outcomes(self, prices: dict[str, float]) -> int:
        """
        Update outcomes for all pending signals.

        Args:
            prices: Current prices by symbol

        Returns:
            Number of signals updated
        """
        updated = 0

        for signal in self._signals.values():
            if signal.symbol in prices:
                old_24h = signal.outcome_24h
                old_7d = signal.outcome_7d

                signal.update_outcome(prices[signal.symbol])

                if signal.outcome_24h != old_24h or signal.outcome_7d != old_7d:
                    updated += 1

        return updated

    def get_stats(self) -> SignalStats:
        """Calculate signal statistics."""
        now = datetime.now()
        day_ago = now - timedelta(hours=24)

        all_signals = list(self._signals.values())
        signals_24h = [s for s in all_signals if s.created_at >= day_ago]

        # Calculate win rates
        completed_24h = [s for s in all_signals if s.outcome_24h != SignalOutcome.PENDING]
        completed_7d = [s for s in all_signals if s.outcome_7d != SignalOutcome.PENDING]

        wins_24h = len([s for s in completed_24h if s.outcome_24h == SignalOutcome.WIN])
        wins_7d = len([s for s in completed_7d if s.outcome_7d == SignalOutcome.WIN])

        win_rate_24h = (wins_24h / len(completed_24h) * 100) if completed_24h else 0
        win_rate_7d = (wins_7d / len(completed_7d) * 100) if completed_7d else 0

        # Average P&L
        pnls_24h = [s.pnl_24h_pct for s in all_signals if s.pnl_24h_pct is not None]
        pnls_7d = [s.pnl_7d_pct for s in all_signals if s.pnl_7d_pct is not None]

        avg_pnl_24h = sum(pnls_24h) / len(pnls_24h) if pnls_24h else 0
        avg_pnl_7d = sum(pnls_7d) / len(pnls_7d) if pnls_7d else 0

        # Find best/worst
        signals_with_pnl = [s for s in all_signals if s.pnl_7d_pct is not None or s.pnl_24h_pct is not None]

        best_signal = None
        worst_signal = None
        if signals_with_pnl:
            sorted_by_pnl = sorted(
                signals_with_pnl,
                key=lambda x: x.pnl_7d_pct or x.pnl_24h_pct or 0,
                reverse=True,
            )
            best_signal = sorted_by_pnl[0]
            worst_signal = sorted_by_pnl[-1]

        # Stats by source
        by_source: dict[str, dict] = {}
        for source in SignalSource:
            source_signals = [s for s in completed_24h if s.source == source]
            if source_signals:
                source_wins = len([s for s in source_signals if s.outcome_24h == SignalOutcome.WIN])
                by_source[source.value] = {
                    "count": len(source_signals),
                    "win_rate": round(source_wins / len(source_signals) * 100, 1),
                }

        # Stats by type
        by_type: dict[str, dict] = {}
        for sig_type in SignalType:
            type_signals = [s for s in completed_24h if s.signal_type == sig_type]
            if type_signals:
                type_wins = len([s for s in type_signals if s.outcome_24h == SignalOutcome.WIN])
                by_type[sig_type.value] = {
                    "count": len(type_signals),
                    "win_rate": round(type_wins / len(type_signals) * 100, 1),
                }

        return SignalStats(
            timestamp=now,
            total_signals=len(all_signals),
            signals_24h=len(signals_24h),
            win_rate_24h=win_rate_24h,
            win_rate_7d=win_rate_7d,
            avg_pnl_24h=avg_pnl_24h,
            avg_pnl_7d=avg_pnl_7d,
            best_signal=best_signal,
            worst_signal=worst_signal,
            by_source=by_source,
            by_type=by_type,
        )

    def _cleanup_old_signals(self) -> None:
        """Remove old signals if over limit."""
        if len(self._signals) > self._max_signals:
            # Remove oldest signals
            sorted_signals = sorted(self._signals.items(), key=lambda x: x[1].created_at)
            to_remove = len(self._signals) - self._max_signals
            for signal_id, _ in sorted_signals[:to_remove]:
                del self._signals[signal_id]


# Global instance
_signal_manager: SignalHistoryManager | None = None


def get_signal_manager() -> SignalHistoryManager:
    """Get global signal manager instance."""
    global _signal_manager
    if _signal_manager is None:
        _signal_manager = SignalHistoryManager()
    return _signal_manager
