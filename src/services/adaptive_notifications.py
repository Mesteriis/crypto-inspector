"""
Adaptive Notifications System - Dynamic alert frequency based on market volatility.

This service monitors market conditions and automatically adjusts notification
frequency to reduce spam during high volatility and increase alerts during
important market movements.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from core.constants import DEFAULT_SYMBOLS
from services.candlestick import CandleInterval, fetch_candlesticks
from services.ha_integration import get_supervisor_client

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MarketVolatility(Enum):
    """Market volatility levels."""
    VERY_LOW = "very_low"    # < 1%
    LOW = "low"              # 1-2%
    MODERATE = "moderate"    # 2-4%
    HIGH = "high"            # 4-8%
    VERY_HIGH = "very_high"  # > 8%


@dataclass
class AdaptiveNotificationRule:
    """Rule for adaptive notifications."""
    
    name: str
    symbol: str
    condition_type: str  # "price_change", "volatility_spike", "trend_change", etc.
    threshold: float
    priority: AlertPriority
    cooldown_minutes: int  # Minimum time between similar alerts
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def can_trigger(self, current_time: datetime) -> bool:
        """Check if rule can be triggered based on cooldown."""
        if not self.enabled:
            return False
            
        if self.last_triggered is None:
            return True
            
        time_since_last = current_time - self.last_triggered
        cooldown_delta = timedelta(minutes=self.cooldown_minutes)
        
        return time_since_last >= cooldown_delta
    
    def record_trigger(self, timestamp: datetime) -> None:
        """Record that this rule was triggered."""
        self.last_triggered = timestamp
        self.trigger_count += 1


@dataclass
class VolatilityProfile:
    """Market volatility profile for adaptive adjustments."""
    
    symbol: str
    current_volatility: float  # Percentage
    volatility_level: MarketVolatility
    price_change_24h: float
    price_change_1h: float
    volume_change: float
    atr: float  # Average True Range
    last_update: datetime
    
    def get_adaptation_factor(self) -> float:
        """Get factor for adjusting notification frequency (0.1 to 3.0)."""
        # Lower factor = less frequent notifications
        # Higher factor = more frequent notifications
        
        if self.volatility_level == MarketVolatility.VERY_LOW:
            return 0.5  # Reduce frequency significantly
        elif self.volatility_level == MarketVolatility.LOW:
            return 0.8  # Slightly reduce frequency
        elif self.volatility_level == MarketVolatility.MODERATE:
            return 1.0  # Normal frequency
        elif self.volatility_level == MarketVolatility.HIGH:
            return 1.5  # Increase frequency
        else:  # VERY_HIGH
            return 2.5  # Significantly increase frequency


class AdaptiveNotificationsManager:
    """Manages adaptive notification system."""
    
    def __init__(self):
        """Initialize adaptive notifications manager."""
        self.rules: List[AdaptiveNotificationRule] = []
        self.volatility_profiles: Dict[str, VolatilityProfile] = {}
        self._supervisor_client = get_supervisor_client()
        self._notification_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        
    async def initialize_default_rules(self) -> None:
        """Initialize default adaptive notification rules."""
        # Price change rules
        self.rules.extend([
            AdaptiveNotificationRule(
                name="significant_price_drop",
                symbol="BTC/USDT",
                condition_type="price_change",
                threshold=-3.0,  # 3% drop
                priority=AlertPriority.HIGH,
                cooldown_minutes=30
            ),
            AdaptiveNotificationRule(
                name="significant_price_jump", 
                symbol="BTC/USDT",
                condition_type="price_change",
                threshold=3.0,  # 3% rise
                priority=AlertPriority.HIGH,
                cooldown_minutes=30
            ),
            AdaptiveNotificationRule(
                name="major_price_move",
                symbol="BTC/USDT", 
                condition_type="price_change",
                threshold=5.0,  # 5% move (either direction)
                priority=AlertPriority.CRITICAL,
                cooldown_minutes=15
            ),
            # ETH rules
            AdaptiveNotificationRule(
                name="eth_significant_move",
                symbol="ETH/USDT",
                condition_type="price_change", 
                threshold=4.0,  # ETH is typically more volatile
                priority=AlertPriority.HIGH,
                cooldown_minutes=25
            )
        ])
        
        logger.info(f"Initialized {len(self.rules)} adaptive notification rules")
    
    async def update_volatility_profiles(self) -> None:
        """Update volatility profiles for all tracked symbols."""
        symbols = [rule.symbol for rule in self.rules]
        unique_symbols = list(set(symbols))
        
        for symbol in unique_symbols:
            try:
                profile = await self._calculate_volatility_profile(symbol)
                self.volatility_profiles[symbol] = profile
                logger.debug(f"Updated volatility profile for {symbol}: {profile.volatility_level.value}")
            except Exception as e:
                logger.error(f"Failed to update volatility profile for {symbol}: {e}")
    
    async def _calculate_volatility_profile(self, symbol: str) -> VolatilityProfile:
        """Calculate volatility profile for a symbol."""
        # Fetch recent candle data
        candles = await fetch_candlesticks(
            symbol=symbol,
            interval=CandleInterval("1h"),
            limit=48  # 48 hours of hourly data
        )
        
        if len(candles) < 10:
            raise ValueError(f"Insufficient data for {symbol}: {len(candles)} candles")
        
        # Calculate price changes
        prices = [float(c.close) for c in candles]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 
                  for i in range(1, len(prices))]
        
        # Calculate current volatility (standard deviation of returns)
        current_volatility = abs(sum(returns[-5:]) / 5) if len(returns) >= 5 else 0
        
        # Calculate 24h and 1h price changes
        price_change_24h = ((prices[-1] - prices[-24]) / prices[-24] * 100) if len(prices) >= 24 else 0
        price_change_1h = ((prices[-1] - prices[-2]) / prices[-2] * 100) if len(prices) >= 2 else 0
        
        # Calculate volume change
        volumes = [float(c.volume) for c in candles]
        volume_change = ((sum(volumes[-5:]) - sum(volumes[-10:-5])) / sum(volumes[-10:-5]) * 100) if len(volumes) >= 10 else 0
        
        # Calculate ATR (Average True Range) approximation
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        tr_values = []
        for i in range(1, len(prices)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - prices[i-1])
            tr3 = abs(lows[i] - prices[i-1])
            tr_values.append(max(tr1, tr2, tr3))
        
        atr = sum(tr_values[-14:]) / 14 if len(tr_values) >= 14 else 0
        atr_percentage = (atr / prices[-1] * 100) if prices[-1] > 0 else 0
        
        # Determine volatility level
        if current_volatility < 1.0:
            volatility_level = MarketVolatility.VERY_LOW
        elif current_volatility < 2.0:
            volatility_level = MarketVolatility.LOW
        elif current_volatility < 4.0:
            volatility_level = MarketVolatility.MODERATE
        elif current_volatility < 8.0:
            volatility_level = MarketVolatility.HIGH
        else:
            volatility_level = MarketVolatility.VERY_HIGH
        
        return VolatilityProfile(
            symbol=symbol,
            current_volatility=current_volatility,
            volatility_level=volatility_level,
            price_change_24h=price_change_24h,
            price_change_1h=price_change_1h,
            volume_change=volume_change,
            atr=atr_percentage,
            last_update=datetime.now()
        )
    
    async def check_and_send_notifications(self) -> List[Dict[str, Any]]:
        """Check all rules and send appropriate notifications."""
        sent_notifications = []
        current_time = datetime.now()
        
        # Update volatility profiles first
        await self.update_volatility_profiles()
        
        # Check each rule
        for rule in self.rules:
            if not rule.can_trigger(current_time):
                continue
                
            try:
                # Get volatility profile for this symbol
                profile = self.volatility_profiles.get(rule.symbol)
                if not profile:
                    continue
                
                # Apply adaptation factor based on volatility
                adaptation_factor = profile.get_adaptation_factor()
                adjusted_threshold = rule.threshold / adaptation_factor
                
                # Check if condition is met
                if await self._check_condition(rule, profile, adjusted_threshold):
                    # Send notification
                    notification = await self._send_notification(rule, profile, current_time)
                    if notification:
                        sent_notifications.append(notification)
                        
                        # Record trigger
                        rule.record_trigger(current_time)
                        
                        # Add to history
                        self._add_to_history(notification)
                        
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
        
        if sent_notifications:
            logger.info(f"Sent {len(sent_notifications)} adaptive notifications")
        
        return sent_notifications
    
    async def _check_condition(
        self,
        rule: AdaptiveNotificationRule,
        profile: VolatilityProfile,
        adjusted_threshold: float
    ) -> bool:
        """Check if rule condition is met with adapted threshold."""
        
        if rule.condition_type == "price_change":
            # Check 1-hour price change against adjusted threshold
            abs_change = abs(profile.price_change_1h)
            meets_threshold = abs_change >= abs(adjusted_threshold)
            
            # Direction check
            if adjusted_threshold > 0:  # Positive threshold
                direction_match = profile.price_change_1h > 0
            else:  # Negative threshold
                direction_match = profile.price_change_1h < 0
            
            return meets_threshold and direction_match
            
        elif rule.condition_type == "volatility_spike":
            # Check if volatility spiked significantly
            baseline_vol = profile.current_volatility * 0.7  # 70% of current as baseline
            spike_threshold = baseline_vol * 1.5  # 50% increase
            return profile.current_volatility >= spike_threshold
            
        elif rule.condition_type == "trend_change":
            # Check for trend reversals (simplified)
            return abs(profile.price_change_1h) > abs(profile.price_change_24h) * 2
            
        return False
    
    async def _send_notification(
        self,
        rule: AdaptiveNotificationRule,
        profile: VolatilityProfile,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Send notification via Home Assistant."""
        if not self._supervisor_client.is_available:
            logger.warning("Supervisor API not available, cannot send notification")
            return None
        
        try:
            # Create notification message
            message = self._format_notification_message(rule, profile)
            title = f"📈 Adaptive Alert: {rule.symbol}"
            
            # Send via persistent notification (can be extended to other services)
            http_client = await self._supervisor_client._get_client()
            
            notification_data = {
                "title": title,
                "message": message,
                "notification_id": f"adaptive_{rule.name}_{int(timestamp.timestamp())}"
            }
            
            response = await http_client.post(
                "/core/api/services/persistent_notification/create",
                json=notification_data
            )
            
            if response.status_code == 200:
                notification_record = {
                    "rule_name": rule.name,
                    "symbol": rule.symbol,
                    "priority": rule.priority.value,
                    "message": message,
                    "volatility_level": profile.volatility_level.value,
                    "adaptation_factor": profile.get_adaptation_factor(),
                    "timestamp": timestamp.isoformat(),
                    "success": True
                }
                
                logger.info(f"Sent adaptive notification: {rule.name} for {rule.symbol}")
                return notification_record
            else:
                logger.error(f"Failed to send notification: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending notification for {rule.name}: {e}")
            return None
    
    def _format_notification_message(
        self,
        rule: AdaptiveNotificationRule,
        profile: VolatilityProfile
    ) -> str:
        """Format notification message with market context."""
        
        base_msg = f"{rule.symbol} triggered '{rule.name}' alert"
        
        if rule.condition_type == "price_change":
            direction = "上涨" if rule.threshold > 0 else "下跌"
            msg = f"{base_msg}\n价格{direction}: {abs(profile.price_change_1h):.2f}% (阈值: {abs(rule.threshold):.1f}%)"
        else:
            msg = f"{base_msg}\n市场波动级别: {profile.volatility_level.value}"
        
        # Add market context
        msg += f"\n📊 当前波动率: {profile.current_volatility:.2f}%"
        msg += f"\n⚡ 24小时变化: {profile.price_change_24h:+.2f}%"
        msg += f"\n⚖️ 调整因子: {profile.get_adaptation_factor():.1f}x"
        
        return msg
    
    def _add_to_history(self, notification: Dict[str, Any]) -> None:
        """Add notification to history with size limit."""
        self._notification_history.append(notification)
        
        # Keep history within size limit
        if len(self._notification_history) > self._max_history_size:
            self._notification_history = self._notification_history[-self._max_history_size:]
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get statistics about notifications."""
        if not self._notification_history:
            return {
                "total_sent": 0,
                "recent_24h": 0,
                "by_priority": {},
                "by_symbol": {}
            }
        
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        recent_notifications = [
            n for n in self._notification_history
            if datetime.fromisoformat(n["timestamp"]) > recent_cutoff
        ]
        
        # Count by priority
        priority_counts = {}
        symbol_counts = {}
        
        for notification in self._notification_history:
            priority = notification["priority"]
            symbol = notification["symbol"]
            
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        return {
            "total_sent": len(self._notification_history),
            "recent_24h": len(recent_notifications),
            "by_priority": priority_counts,
            "by_symbol": symbol_counts,
            "last_notification": self._notification_history[-1]["timestamp"] if self._notification_history else None
        }
    
    def get_active_rules(self) -> List[Dict[str, Any]]:
        """Get list of currently active rules."""
        return [
            {
                "name": rule.name,
                "symbol": rule.symbol,
                "condition_type": rule.condition_type,
                "threshold": rule.threshold,
                "priority": rule.priority.value,
                "cooldown_minutes": rule.cooldown_minutes,
                "enabled": rule.enabled,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                "trigger_count": rule.trigger_count
            }
            for rule in self.rules
            if rule.enabled
        ]
    
    def get_volatility_status(self) -> Dict[str, Any]:
        """Get current volatility status for all symbols."""
        status = {}
        
        for symbol, profile in self.volatility_profiles.items():
            status[symbol] = {
                "current_volatility": profile.current_volatility,
                "volatility_level": profile.volatility_level.value,
                "adaptation_factor": profile.get_adaptation_factor(),
                "price_change_24h": profile.price_change_24h,
                "price_change_1h": profile.price_change_1h,
                "last_update": profile.last_update.isoformat()
            }
        
        return status
    
    async def add_custom_rule(self, rule: AdaptiveNotificationRule) -> bool:
        """Add a custom notification rule."""
        try:
            self.rules.append(rule)
            logger.info(f"Added custom rule: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add custom rule {rule.name}: {e}")
            return False
    
    async def remove_rule(self, rule_name: str) -> bool:
        """Remove a notification rule by name."""
        try:
            self.rules = [rule for rule in self.rules if rule.name != rule_name]
            logger.info(f"Removed rule: {rule_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove rule {rule_name}: {e}")
            return False
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self._notification_history.clear()
        logger.info("Notification history cleared")


# Global instance
_adaptive_notifications: Optional[AdaptiveNotificationsManager] = None


def get_adaptive_notifications() -> AdaptiveNotificationsManager:
    """Get or create global adaptive notifications instance."""
    global _adaptive_notifications
    if _adaptive_notifications is None:
        _adaptive_notifications = AdaptiveNotificationsManager()
    return _adaptive_notifications