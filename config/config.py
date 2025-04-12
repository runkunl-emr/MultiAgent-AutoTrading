import os
import yaml
from typing import Dict, Any
import logging


def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        raise


def get_env_config() -> Dict[str, Any]:
    config = {
        'listener': {
            'discord_token': os.environ.get('DISCORD_TOKEN', ''),
            'channel_ids': os.environ.get('DISCORD_CHANNEL_IDS', '').split(','),
        },
        'broker': {
            'broker_type': os.environ.get('BROKER_TYPE', 'mock'),
            'trading_mode': os.environ.get('TRADING_MODE', 'paper'),
            'credentials': {
                'api_key': os.environ.get('BROKER_API_KEY', ''),
                'api_secret': os.environ.get('BROKER_API_SECRET', ''),
            }
        },
        'risk': {
            'max_position_size': float(os.environ.get('MAX_POSITION_SIZE', '0.02')),
            'max_loss_per_trade': float(os.environ.get('MAX_LOSS_PER_TRADE', '0.01')),
            'daily_loss_limit': float(os.environ.get('DAILY_LOSS_LIMIT', '0.05')),
            'max_open_positions': int(os.environ.get('MAX_OPEN_POSITIONS', '5')),
        }
    }
    return config


def create_default_config(output_path: str) -> None:
    default_config = {
        'listener': {
            'discord_token': 'YOUR_DISCORD_TOKEN',
            'channel_ids': ['CHANNEL_ID_1', 'CHANNEL_ID_2'],
            'reconnect_attempts': 3,
            'message_throttle': 100
        },
        'parser': {
            'formats': ['standard']
        },
        'risk': {
            'max_position_size': 0.02,  # 2% of account
            'max_loss_per_trade': 0.01,  # 1% of account
            'daily_loss_limit': 0.05,    # 5% of account
            'max_open_positions': 5,
            'correlation_threshold': 0.7
        },
        'broker': {
            'broker_type': 'mock',  # 'mock', 'ibkr', etc.
            'trading_mode': 'paper',  # 'paper' or 'live'
            'credentials': {
                'api_key': '',
                'api_secret': ''
            },
            'api_endpoints': {
                'base_url': '',
                'order_endpoint': '/api/orders'
            },
            'connection_timeout': 30
        },
        'logging': {
            'level': 'INFO',
            'file': 'quant_bot.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as file:
        yaml.dump(default_config, file, default_flow_style=False)
        
    print(f"Default configuration created at {output_path}") 