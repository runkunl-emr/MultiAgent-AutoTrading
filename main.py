#!/usr/bin/env python3
import asyncio
import os
import sys
import signal
import argparse
import logging
import yaml
import traceback
from typing import Dict, Any, Optional
from config.config import load_config
from core.orchestrator import TradingOrchestrator
from utils.logging import setup_logging


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_path}: {str(e)}")
        sys.exit(1)


async def main():
    """Main entry point for the trading bot."""
    parser = argparse.ArgumentParser(description='Quantitative Trading Bot')
    parser.add_argument('--config', '-c', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--log-level', '-l', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    parser.add_argument('--dry-run', '-d', action='store_true',
                        help='Dry run mode (no actual trades)')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level, file='logs/trading_bot.log')
    
    # Load configuration
    config_path = args.config
    config = load_config(config_path)
    
    # Override broker settings for dry run if specified
    if args.dry_run:
        logging.warning("DRY RUN MODE ENABLED - No actual trades will be executed")
        if 'broker' not in config:
            config['broker'] = {}
        config['broker']['trading_mode'] = 'paper'
        config['broker']['broker_type'] = 'mock'
    
    # Create trading orchestrator
    try:
        trading_bot = TradingOrchestrator(config)
        
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(shutdown(trading_bot, loop))
            )
        
        # Start the trading bot
        await trading_bot.start()
        
        # Run forever until interrupted
        logging.info("Trading bot is running. Press CTRL+C to stop.")
        await asyncio.Event().wait()  # Run indefinitely
    
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        logging.error(traceback.format_exc())
        sys.exit(1)


async def shutdown(trading_bot: TradingOrchestrator, loop: asyncio.AbstractEventLoop):
    """Gracefully shut down the trading bot."""
    logging.info("Shutting down...")
    
    try:
        await trading_bot.stop()
        
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        loop.stop()
    except Exception as e:
        logging.error(f"Error during shutdown: {str(e)}")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main()) 