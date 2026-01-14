import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.models import AlertInfo, OrderInfo, OrderResult, TradeDirection
from adapters.broker_adapter import BrokerAdapter
from utils.retry import retry_with_backoff
from utils.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self, broker_adapter: BrokerAdapter, config: Dict[str, Any] = None):
        self.broker = broker_adapter
        self.config = config or {}
        self.connected = False
        self.execution_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'avg_execution_time': 0
        }
        
        # Default configuration values
        self.default_order_type = self.config.get('default_order_type', 'MARKET')
        self.auto_connect = self.config.get('auto_connect', True)
        self.default_slippage = self.config.get('default_slippage', 0.001)  # 0.1% slippage by default
        
        # Connect if auto_connect is True
        if self.auto_connect:
            self.connect()
    
    def connect(self) -> bool:
        """Connect to the broker."""
        try:
            result = self.broker.connect()
            self.connected = result
            logger.info(f"Broker connection {'successful' if result else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Failed to connect to broker: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the broker."""
        if not self.connected:
            logger.warning("Not connected to broker, skipping disconnect")
            return
        
        try:
            self.broker.disconnect()
            self.connected = False
            logger.info("Disconnected from broker")
        except Exception as e:
            logger.error(f"Error disconnecting from broker: {str(e)}")
    
    @circuit_breaker(service_name="execute_trade", failure_threshold=3, reset_timeout=60)
    @retry_with_backoff(max_retries=3, backoff_factor=2, jitter=True)
    def execute_trade(self, alert: AlertInfo, quantity: int, correlation_id: Optional[str] = None) -> OrderResult:
        """Execute a trade based on alert information and calculated position size."""
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
            if not self.connected:
                return OrderResult(
                    success=False,
                    error="Not connected to broker",
                    correlation_id=correlation_id or str(uuid.uuid4())
                )
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Log trade execution
        logger.info(f"Executing trade for {alert.symbol} with direction {alert.bias}, "
                   f"quantity {quantity}, correlation_id: {correlation_id}")
        
        start_time = time.time()
        
        # Determine order action based on bias
        action = "BUY" if alert.direction == "bull" else "SELL"
        
        # Apply slippage to the price based on direction
        adjusted_price = None
        if alert.price:
            slippage_factor = 1 + (self.default_slippage if action == "BUY" else -self.default_slippage)
            adjusted_price = alert.price * slippage_factor
        
        # Create order info
        order = OrderInfo(
            symbol=alert.symbol,
            action=action,
            quantity=quantity,
            order_type=self.default_order_type,
            price=adjusted_price,  # None for market orders
            time_in_force="DAY",
            correlation_id=correlation_id,
            alert_timestamp=alert.timestamp
        )
        
        try:
            # Place the order
            result = self.broker.place_order(order)
            
            # Update execution stats
            self._update_execution_stats(result)
            
            # Log the result
            if result.success:
                logger.info(f"Order executed successfully: {result.order_id}, "
                           f"filled price: {result.filled_price}, filled quantity: {result.filled_quantity}")
            else:
                logger.error(f"Order execution failed: {result.error}")
            
            return result
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            logger.error(f"Exception during order execution: {str(e)}")
            
            # Update execution stats
            self.execution_stats['total_trades'] += 1
            self.execution_stats['failed_trades'] += 1
            
            return OrderResult(
                success=False,
                error=str(e),
                correlation_id=correlation_id,
                execution_time=execution_time
            )
    
    def get_account_info(self):
        """Get current account information from the broker."""
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
            if not self.connected:
                logger.error("Failed to connect to broker")
                return None
        
        try:
            return self.broker.get_account_info()
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None
    
    def get_positions(self):
        """Get current positions from the broker."""
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
            if not self.connected:
                logger.error("Failed to connect to broker")
                return {}
        
        try:
            return self.broker.get_positions()
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return {}
    
    def get_order_status(self, order_id: str):
        """Get the status of a specific order."""
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
            if not self.connected:
                logger.error("Failed to connect to broker")
                return {"status": "ERROR", "message": "Not connected to broker"}
        
        try:
            return self.broker.get_order_status(order_id)
        except Exception as e:
            logger.error(f"Failed to get order status: {str(e)}")
            return {"status": "ERROR", "message": str(e)}
    
    def get_execution_stats(self):
        """Get execution statistics."""
        return self.execution_stats
    
    def _update_execution_stats(self, result: OrderResult):
        """Update execution statistics based on order result."""
        self.execution_stats['total_trades'] += 1
        
        if result.success:
            self.execution_stats['successful_trades'] += 1
        else:
            self.execution_stats['failed_trades'] += 1
        
        # Update average execution time
        if result.execution_time:
            current_avg = self.execution_stats['avg_execution_time']
            total_successful = self.execution_stats['successful_trades']
            
            if total_successful == 1:
                self.execution_stats['avg_execution_time'] = result.execution_time
            else:
                # Weighted average calculation
                self.execution_stats['avg_execution_time'] = (
                    (current_avg * (total_successful - 1) + result.execution_time) / total_successful
                ) 