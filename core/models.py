from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime
import uuid
from enum import Enum


class TradeDirection(Enum):
    BULLISH = "bull"
    BEARISH = "bear"


@dataclass
class AlertInfo:
    symbol: str
    price: float
    direction: str  # "bull" or "bear"
    strategy_id: str
    market_data: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "discord"
    confidence: float = 1.0
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_message: str = ""

    @property
    def bias(self) -> str:
        return self.direction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "direction": self.direction,
            "strategy_id": self.strategy_id,
            "market_data": self.market_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "source": self.source,
            "confidence": self.confidence,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }


@dataclass
class RiskResult:
    approved: bool
    reason: Optional[str] = None
    position_size: float = 0.0
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "position_size": self.position_size,
            "risk_score": self.risk_score
        }


@dataclass
class OrderInfo:
    symbol: str
    action: str  # "BUY", "SELL", "SELL_SHORT"
    quantity: int
    order_type: str  # "MKT", "LMT"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_id: Optional[str] = None
    correlation_id: Optional[str] = None
    risk_score: Optional[float] = None
    max_slippage: Optional[float] = None
    time_in_force: str = "DAY"
    alert_timestamp: Optional[datetime] = None


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    correlation_id: Optional[str] = None

    @property
    def error(self) -> Optional[str]:
        return self.error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "order_id": self.order_id,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "correlation_id": self.correlation_id
        }


@dataclass
class AccountInfo:
    balance: float
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    buying_power: Optional[float] = None
    margin_used: Optional[float] = None
    currency: str = "USD" 