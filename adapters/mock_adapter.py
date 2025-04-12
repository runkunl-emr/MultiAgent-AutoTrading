import logging
import uuid
import random
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.models import OrderInfo, OrderResult, AccountInfo
from adapters.broker_adapter import BrokerAdapter

logger = logging.getLogger(__name__)


class MockBrokerAdapter(BrokerAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        
        # Mock account data
        self.balance = config.get('mock_balance', 100000.0)
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.order_execution_delay = config.get('mock_execution_delay', 0.5)  # seconds
        
        # Simulate market prices with a small random offset
        self.market_prices: Dict[str, float] = {}
        
        logger.info("Mock broker adapter initialized")
    
    def connect(self) -> bool:
        logger.info("Connecting to mock broker...")
        time.sleep(0.5)  # Simulate connection delay
        self.connected = True
        logger.info("Connected to mock broker")
        return True
    
    def disconnect(self) -> None:
        logger.info("Disconnecting from mock broker...")
        self.connected = False
        logger.info("Disconnected from mock broker")
    
    def place_order(self, order: OrderInfo) -> OrderResult:
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
        
        logger.info(f"Placing mock order: {order.symbol} {order.action} {order.quantity} shares")
        
        # Generate a unique order ID
        order_id = str(uuid.uuid4())
        
        # Simulate market price (use order price as base with small random variation)
        market_price = self._get_market_price(order.symbol, order.price)
        
        # Add a small delay to simulate order execution
        time.sleep(self.order_execution_delay)
        
        # Create order record
        order_record = {
            'id': order_id,
            'symbol': order.symbol,
            'action': order.action,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'price': order.price,
            'status': 'FILLED',
            'filled_price': market_price,
            'filled_quantity': order.quantity,
            'timestamp': datetime.now().isoformat(),
            'correlation_id': order.correlation_id
        }
        
        # Store order
        self.orders[order_id] = order_record
        
        # Update positions
        self._update_positions(order, market_price)
        
        # Create order result
        result = OrderResult(
            success=True,
            order_id=order_id,
            filled_price=market_price,
            filled_quantity=order.quantity,
            status='FILLED',
            correlation_id=order.correlation_id,
            execution_time=self.order_execution_delay * 1000  # Convert to ms
        )
        
        logger.info(f"Mock order executed: {order_id} at price {market_price}")
        return result
    
    def get_account_info(self) -> AccountInfo:
        if not self.connected:
            logger.warning("Not connected to broker, attempting to connect...")
            self.connect()
        
        # Calculate account value including positions
        positions_value = sum(
            pos['quantity'] * self._get_market_price(symbol, pos['avg_price'])
            for symbol, pos in self.positions.items()
        )
        
        total_value = self.balance + positions_value
        
        return AccountInfo(
            balance=self.balance,
            positions=self.positions,
            buying_power=self.balance,  # Simplification for mock
            margin_used=positions_value
        )
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        return self.positions
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if order_id in self.orders:
            return self.orders[order_id]
        
        return {
            'id': order_id,
            'status': 'NOT_FOUND',
            'message': 'Order not found'
        }
    
    def _get_market_price(self, symbol: str, reference_price: Optional[float] = None) -> float:
        """Get a simulated market price with small random variation."""
        if symbol not in self.market_prices and reference_price is not None:
            # Initialize with reference price
            self.market_prices[symbol] = reference_price
        elif symbol not in self.market_prices:
            # Default price if no reference
            self.market_prices[symbol] = 100.0
        
        # Add small random price movement (-1% to +1%)
        current_price = self.market_prices[symbol]
        movement = random.uniform(-0.01, 0.01) * current_price
        new_price = current_price + movement
        
        # Update stored price
        self.market_prices[symbol] = new_price
        
        return new_price
    
    def _update_positions(self, order: OrderInfo, executed_price: float) -> None:
        """Update positions after an order execution."""
        symbol = order.symbol
        quantity = order.quantity
        
        # For buy orders, add to position
        if order.action == "BUY":
            if symbol in self.positions:
                # Update existing position
                current_pos = self.positions[symbol]
                new_quantity = current_pos['quantity'] + quantity
                avg_price = (current_pos['avg_price'] * current_pos['quantity'] + 
                             executed_price * quantity) / new_quantity
                
                self.positions[symbol] = {
                    'quantity': new_quantity,
                    'avg_price': avg_price,
                    'last_price': executed_price
                }
            else:
                # Create new position
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_price': executed_price,
                    'last_price': executed_price
                }
            
            # Deduct from balance
            self.balance -= executed_price * quantity
        
        # For sell orders, reduce position
        elif order.action == "SELL" or order.action == "SELL_SHORT":
            if symbol in self.positions and self.positions[symbol]['quantity'] >= quantity:
                # Reduce existing position
                current_pos = self.positions[symbol]
                new_quantity = current_pos['quantity'] - quantity
                
                if new_quantity > 0:
                    # Update position
                    self.positions[symbol]['quantity'] = new_quantity
                    self.positions[symbol]['last_price'] = executed_price
                else:
                    # Remove position if fully sold
                    del self.positions[symbol]
                
                # Add to balance
                self.balance += executed_price * quantity
            else:
                # Short selling or selling without position (for mock we'll allow it)
                self.positions[symbol] = {
                    'quantity': -quantity,  # Negative for short
                    'avg_price': executed_price,
                    'last_price': executed_price
                }
                
                # Add to balance for the sale
                self.balance += executed_price * quantity
        
        logger.debug(f"Updated positions: {self.positions}")
        logger.debug(f"Updated balance: {self.balance}") 