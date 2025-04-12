from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from core.models import OrderInfo, OrderResult, AccountInfo


class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker API."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the broker API."""
        pass
    
    @abstractmethod
    def place_order(self, order: OrderInfo) -> OrderResult:
        """Place a trading order."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """Get account information."""
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get current positions."""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        pass


class BrokerAdapterFactory:
    @staticmethod
    def create(config: Dict[str, Any]) -> BrokerAdapter:
        """Create an appropriate broker adapter based on configuration."""
        broker_type = config.get('broker_type', 'mock').lower()
        trading_mode = config.get('trading_mode', 'paper').lower()
        
        # Import here to avoid circular imports
        from adapters.mock_adapter import MockBrokerAdapter
        
        # If using paper trading mode or specifically requesting mock adapter
        if trading_mode == 'paper' or broker_type == 'mock':
            return MockBrokerAdapter(config)
        
        # For live trading with IBKR
        if broker_type == 'ibkr':
            try:
                from adapters.ibkr_adapter import IBKRBrokerAdapter
                return IBKRBrokerAdapter(config)
            except ImportError:
                import logging
                logging.warning("IBKR adapter requested but not available, falling back to mock adapter")
                return MockBrokerAdapter(config)
        
        # For MooMoo/Futu
        if broker_type == 'moomoo':
            try:
                from adapters.moomoo_adapter import MooMooBrokerAdapter
                return MooMooBrokerAdapter(config)
            except ImportError:
                import logging
                logging.warning("MooMoo adapter requested but not available, falling back to mock adapter")
                return MockBrokerAdapter(config)
        
        # Default to mock adapter if broker type is unknown
        import logging
        logging.warning(f"Unknown broker type '{broker_type}', using mock adapter")
        return MockBrokerAdapter(config) 