#!/usr/bin/env python3
import asyncio
import logging
import argparse
import yaml
from datetime import datetime
import uuid

from core.models import AlertInfo, TradeDirection
from core.orchestrator import TradingOrchestrator
from utils.logging import setup_logging

# Sample alert messages for testing
SAMPLE_ALERTS = [
    # Standard format
    """🚨 SIGNAL ALERT 🚨
Symbol: AAPL
Direction: BULLISH
Entry Price: 185.50
Target: 190.00
Stop Loss: 180.00
Strategy: Breakout
Time Frame: 1h
Confidence: High
""",
    # Another format
    """🔔 Trading Opportunity 🔔
BUY $MSFT at $350.75
Take profit: $360.00
Stop loss: $345.00
Technical setup: Cup and Handle
""",
    # Chinese format
    """📊 交易信号 📊
币种: BTC/USDT
方向: 看涨
入场价: 65000
目标价: 70000
止损: 62000
策略: 突破
"""
]


async def test_discord_parsing(orchestrator, test_message):
    """Test Discord message parsing without actual trading."""
    print(f"\n--- Testing Discord message parsing ---")
    print(f"Message:\n{test_message}\n")
    
    # Manually trigger the message processing (simulating Discord listener)
    result = orchestrator.process_message(test_message)
    
    print(f"Processed successfully: {result}")
    print(f"Current stats: {orchestrator.get_stats()}")
    
    # Wait a moment to allow all async operations to complete
    await asyncio.sleep(1)


async def test_manual_trade(orchestrator):
    """Test manual trade execution."""
    print(f"\n--- Testing manual trade execution ---")
    
    # Create a sample alert
    alert = AlertInfo(
        symbol="TSLA",
        bias=TradeDirection.BULLISH,
        price=900.0,
        strategy="Manual Test",
        correlation_id=str(uuid.uuid4()),
        timestamp=datetime.now()
    )
    
    print(f"Executing manual trade for {alert.symbol} at ${alert.price}")
    
    # Execute the trade
    result = orchestrator.execute_manual_trade(alert)
    
    print(f"Trade execution result: {result.success}")
    if result.success:
        print(f"Order ID: {result.order_id}")
        print(f"Filled price: {result.filled_price}")
        print(f"Filled quantity: {result.filled_quantity}")
    else:
        print(f"Error: {result.error}")
    
    print(f"Current stats: {orchestrator.get_stats()}")
    
    # Wait a moment to allow all async operations to complete
    await asyncio.sleep(1)


async def test_rejected_trade(orchestrator):
    """Test a trade that should be rejected by risk management."""
    print(f"\n--- Testing rejected trade ---")
    
    # Create a risky alert (using a blacklisted symbol or excessive quantity)
    alert = AlertInfo(
        symbol="BLACKLISTED",  # This should be rejected if configured correctly
        bias=TradeDirection.BULLISH,
        price=1000.0,
        strategy="Risky Test",
        correlation_id=str(uuid.uuid4()),
        timestamp=datetime.now()
    )
    
    print(f"Executing risky trade for {alert.symbol} at ${alert.price}")
    
    # Execute the trade
    result = orchestrator.execute_manual_trade(alert)
    
    print(f"Trade execution result: {result.success}")
    print(f"Error/Reason: {result.error}")
    print(f"Current stats: {orchestrator.get_stats()}")
    
    # Wait a moment to allow all async operations to complete
    await asyncio.sleep(1)


async def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description='Test Quantitative Trading Bot')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    parser.add_argument('--test', type=str, choices=['all', 'parsing', 'manual', 'rejected'],
                        default='all', help='Test type to run')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level, file='logs/test_bot.log')
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        return
    
    # Ensure we're in paper/mock mode for testing
    if 'broker' not in config:
        config['broker'] = {}
    config['broker']['trading_mode'] = 'paper'
    config['broker']['broker_type'] = 'mock'
    
    # Add a blacklisted symbol for testing rejection
    if 'risk_management' not in config:
        config['risk_management'] = {}
    if 'blacklisted_symbols' not in config['risk_management']:
        config['risk_management']['blacklisted_symbols'] = []
    config['risk_management']['blacklisted_symbols'].append('BLACKLISTED')
    
    # Create trading orchestrator
    try:
        trading_bot = TradingOrchestrator(config)
        
        # Run the requested tests
        if args.test in ['all', 'parsing']:
            for i, message in enumerate(SAMPLE_ALERTS):
                await test_discord_parsing(trading_bot, message)
        
        if args.test in ['all', 'manual']:
            await test_manual_trade(trading_bot)
        
        if args.test in ['all', 'rejected']:
            await test_rejected_trade(trading_bot)
        
    except Exception as e:
        logging.error(f"Error in test: {str(e)}")
        logging.exception(e)


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main()) 