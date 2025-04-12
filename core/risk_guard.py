import logging
import time
from typing import Dict, Optional, Any, List, Set
from datetime import datetime, timedelta

from core.models import AlertInfo, OrderInfo, AccountInfo

logger = logging.getLogger(__name__)


class RiskGuardService:
    def __init__(self, config: Dict[str, Any], account_info_provider: Any = None):
        self.config = config
        self.account_info_provider = account_info_provider
        
        # Default risk parameters
        self.max_position_size = config.get('max_position_size', 0.02)  # 2% of account
        self.max_loss_per_trade = config.get('max_loss_per_trade', 0.01)  # 1% of account
        self.daily_loss_limit = config.get('daily_loss_limit', 0.05)  # 5% of account
        self.max_open_positions = config.get('max_open_positions', 5)
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        
        # Track recent trades to avoid duplicates
        self.recent_trades: Dict[str, datetime] = {}
        self.cooldown_period = timedelta(minutes=5)  # Time to wait before allowing same signal
        
        # Track daily P&L
        self.daily_pnl = 0.0
        self.daily_pnl_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Blacklisted symbols
        self.blacklisted_symbols: Set[str] = set()
        
        # Load additional config if available
        self._load_additional_config()
    
    def _load_additional_config(self):
        # Load any additional risk config parameters
        if 'risk' in self.config:
            risk_config = self.config['risk']
            self.max_position_size = risk_config.get('max_position_size', self.max_position_size)
            self.max_loss_per_trade = risk_config.get('max_loss_per_trade', self.max_loss_per_trade)
            self.daily_loss_limit = risk_config.get('daily_loss_limit', self.daily_loss_limit)
            self.max_open_positions = risk_config.get('max_open_positions', self.max_open_positions)
            self.correlation_threshold = risk_config.get('correlation_threshold', self.correlation_threshold)
            
            # Load any blacklisted symbols
            blacklist = risk_config.get('blacklisted_symbols', [])
            self.blacklisted_symbols = set(blacklist)
    
    def evaluate_alert(self, alert: AlertInfo) -> Optional[OrderInfo]:
        # Reset daily P&L if needed
        self._check_daily_reset()
        
        # Check if symbol is blacklisted
        if alert.symbol in self.blacklisted_symbols:
            logger.warning(f"Symbol {alert.symbol} is blacklisted, rejecting alert")
            return None
        
        # Check for duplicate signals (same symbol, same direction, within cooldown)
        trade_key = f"{alert.symbol}_{alert.direction}"
        if trade_key in self.recent_trades:
            last_time = self.recent_trades[trade_key]
            if datetime.now() - last_time < self.cooldown_period:
                logger.info(f"Ignoring duplicate signal for {alert.symbol} {alert.direction} "
                           f"(cooldown: {self.cooldown_period})")
                return None
        
        # Get account info
        account_info = self._get_account_info()
        if not account_info:
            logger.error("Failed to get account info, rejecting alert")
            return None
        
        # Check if we're over the daily loss limit
        if self.daily_pnl <= -1 * self.daily_loss_limit * account_info.balance:
            logger.warning(f"Daily loss limit reached ({self.daily_pnl:.2f}), rejecting all new trades")
            return None
        
        # Check if we have too many open positions
        current_positions = len(account_info.positions)
        if current_positions >= self.max_open_positions:
            logger.warning(f"Maximum number of open positions reached ({current_positions}), rejecting alert")
            return None
        
        # Calculate position size
        position_size, quantity = self._calculate_position_size(alert, account_info)
        if quantity <= 0:
            logger.warning(f"Calculated quantity is zero or negative, rejecting alert")
            return None
        
        # Determine action based on direction
        action = "BUY" if alert.direction == "bull" else "SELL_SHORT"
        
        # Create order info
        order_info = OrderInfo(
            symbol=alert.symbol,
            action=action,
            quantity=quantity,
            order_type="MKT",  # Default to market order for P0
            price=alert.price,  # Reference price
            correlation_id=alert.correlation_id,
            strategy_id=alert.strategy_id,
            # For P0, we're not setting stop_loss and take_profit yet
        )
        
        # Update recent trades
        self.recent_trades[trade_key] = datetime.now()
        
        logger.info(f"Alert evaluation successful: {alert.symbol} {action} {quantity} shares")
        return order_info
    
    def _get_account_info(self) -> Optional[AccountInfo]:
        if self.account_info_provider:
            try:
                return self.account_info_provider.get_account_info()
            except Exception as e:
                logger.error(f"Error getting account info: {e}")
                return None
        
        # Default mock account for P0
        return AccountInfo(
            balance=100000.0,  # $100k mock account
            positions={},
            buying_power=100000.0
        )
    
    def _calculate_position_size(self, alert: AlertInfo, account: AccountInfo) -> (float, int):
        # Calculate maximum dollar amount to risk (based on account balance)
        max_dollar_risk = account.balance * self.max_position_size
        
        # Simple position sizing for P0 - fixed percentage of account
        position_dollar_size = max_dollar_risk
        
        # Calculate quantity based on current price
        if alert.price <= 0:
            return 0, 0
        
        quantity = int(position_dollar_size / alert.price)
        
        # Ensure minimum quantity
        if quantity < 1:
            quantity = 1
        
        logger.debug(f"Calculated position size: ${position_dollar_size:.2f}, {quantity} shares")
        return position_dollar_size, quantity
    
    def _check_daily_reset(self):
        now = datetime.now()
        if now.date() > self.daily_pnl_reset_time.date():
            logger.info(f"Resetting daily P&L from {self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.daily_pnl_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def update_daily_pnl(self, pnl_change: float):
        self.daily_pnl += pnl_change
        logger.info(f"Updated daily P&L: {self.daily_pnl:.2f}")
    
    def set_risk_parameters(self, params: Dict[str, Any]):
        if 'max_position_size' in params:
            self.max_position_size = params['max_position_size']
        
        if 'max_loss_per_trade' in params:
            self.max_loss_per_trade = params['max_loss_per_trade']
        
        if 'daily_loss_limit' in params:
            self.daily_loss_limit = params['daily_loss_limit']
        
        if 'max_open_positions' in params:
            self.max_open_positions = params['max_open_positions']
        
        if 'correlation_threshold' in params:
            self.correlation_threshold = params['correlation_threshold']
        
        if 'blacklisted_symbols' in params:
            self.blacklisted_symbols = set(params['blacklisted_symbols'])
        
        logger.info(f"Risk parameters updated: max_position_size={self.max_position_size}, "
                   f"max_loss_per_trade={self.max_loss_per_trade}, daily_loss_limit={self.daily_loss_limit}")
    
    def add_to_blacklist(self, symbol: str):
        self.blacklisted_symbols.add(symbol)
        logger.info(f"Added {symbol} to blacklist")
    
    def remove_from_blacklist(self, symbol: str):
        if symbol in self.blacklisted_symbols:
            self.blacklisted_symbols.remove(symbol)
            logger.info(f"Removed {symbol} from blacklist") 