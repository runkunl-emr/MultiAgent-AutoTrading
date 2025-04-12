import re
import logging
from typing import Optional, Dict, Any, List, Type, Pattern
from datetime import datetime
from abc import ABC, abstractmethod

from core.models import AlertInfo

logger = logging.getLogger(__name__)


class AlertParser(ABC):
    @abstractmethod
    def parse_alert(self, message: str) -> Optional[AlertInfo]:
        pass
    
    @abstractmethod
    def can_parse(self, message: str) -> bool:
        pass


class StandardAlertParser(AlertParser):
    def __init__(self):
        # Pattern for standard alert format
        # Example:
        # Bullish Bias
        # Detected Symbol: NQ
        # Price: 19656.00
        # Strategy: OrderFlowBot3.5 (ID 3)
        # Market: NDX 19455.68, SPX 4561.37
        self.bias_pattern = re.compile(r'(Bullish|Bearish)\s+Bias', re.IGNORECASE)
        self.symbol_pattern = re.compile(r'Detected\s+Symbol:\s+(\w+)', re.IGNORECASE)
        self.price_pattern = re.compile(r'Price:\s+([\d\.]+)', re.IGNORECASE)
        self.strategy_pattern = re.compile(r'Strategy:\s+([\w\.]+)(?:\s+\(ID\s+(\d+)\))?', re.IGNORECASE)
        self.market_pattern = re.compile(r'Market:\s+(.*?)(?:\n|$)', re.IGNORECASE)
    
    def can_parse(self, message: str) -> bool:
        return bool(self.bias_pattern.search(message) and self.symbol_pattern.search(message))
    
    def parse_alert(self, message: str) -> Optional[AlertInfo]:
        try:
            # Extract direction (bull/bear)
            bias_match = self.bias_pattern.search(message)
            if not bias_match:
                logger.warning("No bias (bullish/bearish) found in message")
                return None
            
            direction = 'bull' if bias_match.group(1).lower() == 'bullish' else 'bear'
            
            # Extract symbol
            symbol_match = self.symbol_pattern.search(message)
            if not symbol_match:
                logger.warning("No symbol found in message")
                return None
            
            symbol = symbol_match.group(1)
            
            # Extract price
            price_match = self.price_pattern.search(message)
            if not price_match:
                logger.warning("No price found in message")
                return None
            
            price = float(price_match.group(1))
            
            # Extract strategy
            strategy_id = "unknown"
            strategy_match = self.strategy_pattern.search(message)
            if strategy_match:
                strategy_name = strategy_match.group(1)
                strategy_id_match = strategy_match.group(2)
                strategy_id = strategy_id_match if strategy_id_match else strategy_name
            
            # Extract market data
            market_data = {}
            market_match = self.market_pattern.search(message)
            if market_match:
                market_str = market_match.group(1)
                # Parse market data in format: "NDX 19455.68, SPX 4561.37"
                items = market_str.split(',')
                for item in items:
                    parts = item.strip().split()
                    if len(parts) >= 2:
                        try:
                            market_data[parts[0]] = float(parts[1])
                        except (ValueError, IndexError):
                            logger.debug(f"Could not parse market data: {item}")
            
            return AlertInfo(
                symbol=symbol,
                price=price,
                direction=direction,
                strategy_id=strategy_id,
                market_data=market_data,
                timestamp=datetime.now(),
                source="discord"
            )
        
        except Exception as e:
            logger.error(f"Error parsing alert message: {e}")
            return None


class ChineseAlertParser(AlertParser):
    def __init__(self):
        # Pattern for Chinese format alerts
        self.direction_pattern = re.compile(r'(看多|看空)', re.IGNORECASE)
        self.symbol_pattern = re.compile(r'标的[：:]\s*(\w+)', re.IGNORECASE)
        self.price_pattern = re.compile(r'价格[：:]\s*([\d\.]+)', re.IGNORECASE)
        self.strategy_pattern = re.compile(r'策略[：:]\s*([\w\.]+)(?:\s*\(ID\s*(\d+)\))?', re.IGNORECASE)
    
    def can_parse(self, message: str) -> bool:
        return bool(self.direction_pattern.search(message) and self.symbol_pattern.search(message))
    
    def parse_alert(self, message: str) -> Optional[AlertInfo]:
        try:
            # Extract direction (bull/bear)
            direction_match = self.direction_pattern.search(message)
            if not direction_match:
                return None
            
            direction = 'bull' if direction_match.group(1) == '看多' else 'bear'
            
            # Extract symbol
            symbol_match = self.symbol_pattern.search(message)
            if not symbol_match:
                return None
            
            symbol = symbol_match.group(1)
            
            # Extract price
            price_match = self.price_pattern.search(message)
            if not price_match:
                return None
            
            price = float(price_match.group(1))
            
            # Extract strategy
            strategy_id = "unknown"
            strategy_match = self.strategy_pattern.search(message)
            if strategy_match:
                strategy_name = strategy_match.group(1)
                strategy_id_match = strategy_match.group(2)
                strategy_id = strategy_id_match if strategy_id_match else strategy_name
            
            return AlertInfo(
                symbol=symbol,
                price=price,
                direction=direction,
                strategy_id=strategy_id,
                market_data={},
                timestamp=datetime.now(),
                source="discord"
            )
        
        except Exception as e:
            logger.error(f"Error parsing Chinese alert message: {e}")
            return None


class ParserFactory:
    def __init__(self, config: Dict[str, Any] = None):
        self.parsers: List[AlertParser] = []
        self.config = config or {}
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        # Always add standard parser
        self.parsers.append(StandardAlertParser())
        
        # Add Chinese parser if needed
        if 'chinese' in self.config.get('formats', []):
            self.parsers.append(ChineseAlertParser())
        
        # Add other parsers based on config
        logger.info(f"Initialized {len(self.parsers)} alert parsers")
    
    def parse_alert(self, message: str) -> Optional[AlertInfo]:
        for parser in self.parsers:
            if parser.can_parse(message):
                return parser.parse_alert(message)
        
        logger.warning("No parser could handle the message format")
        return None
    
    def detect_language(self, message: str) -> str:
        # Simple language detection based on character sets
        # This is a very basic implementation
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', message))
        if chinese_chars > 5:  # If more than 5 Chinese characters
            return "chinese"
        return "english" 