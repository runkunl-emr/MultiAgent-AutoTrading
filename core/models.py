from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import uuid


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


@dataclass
class AccountInfo:
    balance: float
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    buying_power: Optional[float] = None
    margin_used: Optional[float] = None
    currency: str = "USD" 