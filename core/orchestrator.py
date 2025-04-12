import asyncio
import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
import traceback

from core.models import AlertInfo, OrderResult
from core.listener import DiscordListener
from core.parser import ParserFactory
from core.risk_guard import RiskGuardService
from core.executor import ExecutionService
from utils.circuit_breaker import CircuitBreaker
from utils.logging import log_with_context

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.correlation_ids: Set[str] = set()
        self.processed_alerts: Dict[str, datetime] = {}  # Message hash -> processed time
        self.stats = {
            'alerts_received': 0,
            'alerts_processed': 0,
            'alerts_rejected': 0,
            'alerts_failed': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_failed': 0
        }
        
        # Initialize components
        self._init_components()
        
        # Circuit breakers for external services
        self.circuit_breakers = {
            'parser': CircuitBreaker(service_name="parser", failure_threshold=3, reset_timeout=60),
            'risk_guard': CircuitBreaker(service_name="risk_guard", failure_threshold=3, reset_timeout=60),
            'executor': CircuitBreaker(service_name="executor", failure_threshold=3, reset_timeout=60),
        }
        
        # Callback functions
        self.alert_callbacks: List[Callable[[AlertInfo], None]] = []
        self.order_callbacks: List[Callable[[OrderResult], None]] = []
        
        # Duplicate message prevention - configurable window (seconds)
        self.duplicate_window = config.get('duplicate_window', 60)
        
        logger.info("Trading orchestrator initialized")
    
    def _init_components(self):
        """Initialize all the components required for trading."""
        try:
            # Initialize parser factory
            parser_config = self.config.get('parser', {})
            self.parser_factory = ParserFactory(parser_config)
            logger.info("Parser factory initialized")
            
            # Initialize risk guard
            risk_config = self.config.get('risk_management', {})
            self.risk_guard = RiskGuardService(risk_config)
            logger.info("Risk guard service initialized")
            
            # Initialize broker adapter and execution service
            from adapters.broker_adapter import BrokerAdapterFactory
            broker_config = self.config.get('broker', {})
            broker_adapter = BrokerAdapterFactory.create_adapter(broker_config)
            
            execution_config = self.config.get('execution', {})
            self.executor = ExecutionService(broker_adapter, execution_config)
            logger.info(f"Execution service initialized with broker type: {broker_config.get('broker_type', 'unknown')}")
            
            # Initialize Discord listener
            listener_config = self.config.get('listener', {})
            discord_token = listener_config.get('discord_token')
            channel_ids = listener_config.get('channel_ids', [])
            
            if discord_token and channel_ids:
                self.listener = DiscordListener(
                    token=discord_token,
                    channel_ids=channel_ids,
                    message_callback=self.process_message,
                    reconnect_attempts=listener_config.get('reconnect_attempts', 3),
                    message_throttle=listener_config.get('message_throttle', 0.5)
                )
                logger.info("Discord listener initialized")
            else:
                self.listener = None
                logger.warning("Discord listener not initialized: missing token or channel IDs")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def start(self):
        """Start the trading bot."""
        logger.info("Starting trading orchestrator...")
        
        if self.listener:
            # Start Discord listener
            logger.info("Starting Discord listener...")
            await self.listener.start()
        else:
            logger.warning("No listener configured, bot is in manual mode")
    
    async def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading orchestrator...")
        
        if self.listener:
            # Stop Discord listener
            logger.info("Stopping Discord listener...")
            await self.listener.stop()
        
        # Disconnect from broker
        logger.info("Disconnecting from broker...")
        self.executor.disconnect()
        
        logger.info("Trading orchestrator stopped")
    
    def process_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Process a message from the listener."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        self.correlation_ids.add(correlation_id)
        
        # Update stats
        self.stats['alerts_received'] += 1
        
        # Check for duplicate messages (using hash of content)
        message_hash = hash(message)
        now = datetime.now()
        
        if message_hash in self.processed_alerts:
            last_processed = self.processed_alerts[message_hash]
            if now - last_processed < timedelta(seconds=self.duplicate_window):
                logger.info(f"Duplicate message detected (within {self.duplicate_window}s window), skipping")
                self.stats['alerts_rejected'] += 1
                return False
        
        # Parse message
        try:
            with self.circuit_breakers['parser']:
                parsed_alert = self.parser_factory.parse_alert(message)
                
                if not parsed_alert:
                    logger.warning(f"Failed to parse message: {message[:100]}...")
                    self.stats['alerts_failed'] += 1
                    return False
                
                # Add correlation ID and metadata
                parsed_alert.correlation_id = correlation_id
                parsed_alert.metadata = metadata or {}
                parsed_alert.raw_message = message
                
                # Update timestamp if not set
                if not parsed_alert.timestamp:
                    parsed_alert.timestamp = datetime.now()
        
        except Exception as e:
            log_with_context(
                logger.error,
                f"Error parsing message: {str(e)}",
                correlation_id=correlation_id
            )
            self.stats['alerts_failed'] += 1
            return False
        
        # Log parsed alert
        log_with_context(
            logger.info,
            f"Parsed alert: {parsed_alert.symbol} {parsed_alert.bias} at {parsed_alert.price}",
            correlation_id=correlation_id,
            data={"alert": parsed_alert.to_dict()}
        )
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(parsed_alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
        
        # Evaluate with risk guard
        try:
            with self.circuit_breakers['risk_guard']:
                risk_result = self.risk_guard.evaluate_alert(parsed_alert)
                
                if not risk_result.approved:
                    log_with_context(
                        logger.warning,
                        f"Risk guard rejected alert: {risk_result.reason}",
                        correlation_id=correlation_id,
                        data={"risk_result": risk_result.to_dict()}
                    )
                    self.stats['alerts_rejected'] += 1
                    return False
                
                quantity = risk_result.position_size
        
        except Exception as e:
            log_with_context(
                logger.error,
                f"Error in risk evaluation: {str(e)}",
                correlation_id=correlation_id
            )
            self.stats['alerts_failed'] += 1
            return False
        
        # Execute trade
        try:
            with self.circuit_breakers['executor']:
                order_result = self.executor.execute_trade(
                    parsed_alert, 
                    quantity,
                    correlation_id
                )
                
                if order_result.success:
                    log_with_context(
                        logger.info,
                        f"Order executed: {parsed_alert.symbol} {parsed_alert.bias} {quantity} shares",
                        correlation_id=correlation_id,
                        data={"order_result": order_result.to_dict()}
                    )
                    self.stats['orders_placed'] += 1
                    self.stats['orders_filled'] += 1
                else:
                    log_with_context(
                        logger.error,
                        f"Order execution failed: {order_result.error}",
                        correlation_id=correlation_id,
                        data={"order_result": order_result.to_dict()}
                    )
                    self.stats['orders_failed'] += 1
                
                # Call order callbacks
                for callback in self.order_callbacks:
                    try:
                        callback(order_result)
                    except Exception as e:
                        logger.error(f"Error in order callback: {str(e)}")
                
                # Update processed alerts to prevent duplicates
                self.processed_alerts[message_hash] = now
                
                # Update stats
                self.stats['alerts_processed'] += 1
                
                return order_result.success
        
        except Exception as e:
            log_with_context(
                logger.error,
                f"Error in trade execution: {str(e)}",
                correlation_id=correlation_id
            )
            self.stats['orders_failed'] += 1
            return False
    
    def execute_manual_trade(self, alert_info: AlertInfo) -> OrderResult:
        """Execute a trade manually with the provided alert info."""
        correlation_id = alert_info.correlation_id or str(uuid.uuid4())
        
        # Evaluate with risk guard
        try:
            risk_result = self.risk_guard.evaluate_alert(alert_info)
            
            if not risk_result.approved:
                log_with_context(
                    logger.warning,
                    f"Risk guard rejected manual alert: {risk_result.reason}",
                    correlation_id=correlation_id
                )
                return OrderResult(
                    success=False,
                    error=f"Risk guard rejected: {risk_result.reason}",
                    correlation_id=correlation_id
                )
            
            quantity = risk_result.position_size
        
        except Exception as e:
            log_with_context(
                logger.error,
                f"Error in risk evaluation for manual trade: {str(e)}",
                correlation_id=correlation_id
            )
            return OrderResult(
                success=False,
                error=f"Risk evaluation error: {str(e)}",
                correlation_id=correlation_id
            )
        
        # Execute trade
        try:
            order_result = self.executor.execute_trade(
                alert_info, 
                quantity,
                correlation_id
            )
            
            if order_result.success:
                log_with_context(
                    logger.info,
                    f"Manual order executed: {alert_info.symbol} {alert_info.bias} {quantity} shares",
                    correlation_id=correlation_id
                )
            else:
                log_with_context(
                    logger.error,
                    f"Manual order execution failed: {order_result.error}",
                    correlation_id=correlation_id
                )
            
            return order_result
        
        except Exception as e:
            log_with_context(
                logger.error,
                f"Error in manual trade execution: {str(e)}",
                correlation_id=correlation_id
            )
            return OrderResult(
                success=False,
                error=f"Execution error: {str(e)}",
                correlation_id=correlation_id
            )
    
    def add_alert_callback(self, callback: Callable[[AlertInfo], None]):
        """Add a callback function for alerts."""
        self.alert_callbacks.append(callback)
    
    def add_order_callback(self, callback: Callable[[OrderResult], None]):
        """Add a callback function for orders."""
        self.order_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for the trading orchestrator."""
        return {
            **self.stats,
            'executor_stats': self.executor.get_execution_stats()
        } 