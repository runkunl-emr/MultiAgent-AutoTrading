# Quantitative Trading Bot

Automated trading system that monitors Discord alerts and executes trades.

## Project Overview

This project implements a complete quantitative trading bot capable of monitoring trading signals in Discord channels, parsing signal content, conducting risk assessment, and executing trades through broker APIs. Particularly suitable for traders who need to respond quickly to trading opportunities.

### Features

- Discord message monitoring and processing
- Support for multiple signal formats (including English and Chinese)
- Configurable risk management system
- Paper trading and live trading modes
- Circuit breakers and automatic retry mechanisms for enhanced system stability
- Detailed logging and trade statistics
- Simple and efficient configuration interface

## Project Structure

```
quant_trading_bot/
├── adapters/            # External service adapters
│   ├── broker_adapter.py  # Broker adapter interface
│   ├── ibkr_adapter.py    # Interactive Brokers adapter
│   └── mock_adapter.py    # Mock trading adapter
├── config/              # Configuration files
│   ├── config.py          # Config loading
│   └── config_template.yaml  # Config template
├── core/                # Core functionality modules
│   ├── executor.py        # Trade execution
│   ├── listener.py        # Discord message listener
│   ├── models.py          # Data models
│   ├── orchestrator.py    # Module coordination
│   ├── parser.py          # Trading signal parser
│   └── risk_guard.py      # Risk control
├── utils/               # Utility modules
│   ├── circuit_breaker.py # Circuit breaker
│   ├── logging.py         # Logging utilities
│   └── retry.py           # Retry mechanism
├── logs/                # Log files directory
├── main.py              # Main program entry
├── test_bot.py          # Test script
└── requirements.txt     # Dependencies
```

## Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/quant_trading_bot.git
cd quant_trading_bot
```

2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

1. Create a configuration file from the template

```bash
cp quant_trading_bot/config/config_template.yaml quant_trading_bot/config/config.yaml
```

2. Edit the configuration file to set Discord token, channel IDs, risk parameters, and broker information

The configuration file contains the following main sections:

- `listener`: Discord listener configuration
- `parser`: Parser configuration
- `risk_management`: Risk management parameters
- `broker`: Broker configuration
- `execution`: Execution settings
- `logging`: Logging configuration

## Running

### Basic Usage

```bash
python -m quant_trading_bot.main --config quant_trading_bot/config/config.yaml
```

### Parameter Description

- `--config`, `-c`: Configuration file path (default: config/config.yaml)
- `--log-level`, `-l`: Logging level (default: INFO)
- `--dry-run`, `-d`: Test mode, no actual trades executed

### Examples

```bash
# Run with DEBUG log level
python -m quant_trading_bot.main --log-level DEBUG

# Run in test mode (no actual trades)
python -m quant_trading_bot.main --dry-run
```

## Testing

You can use the test script to verify functionality of different parts of the system:

```bash
python -m quant_trading_bot.test_bot --test all
```

Test options:
- `all`: Run all tests
- `parsing`: Test message parsing
- `manual`: Test manual trade execution
- `rejected`: Test risk control trade rejection

## Development

### Adding a New Broker Adapter

1. Create a new adapter file in the `adapters` directory
2. Inherit from the `BrokerAdapter` class and implement all required methods
3. Add creation logic for the new adapter in the `BrokerAdapterFactory`

### Adding a New Signal Format

1. Add a new parser class in `core/parser.py`
2. Inherit from the `AlertParser` class and implement the `can_parse` and `parse_alert` methods
3. Register the new parser in the `ParserFactory`

## Development Progress Tracking

This section tracks the development status of various components.

### Discord Listener Module

| Feature | Status | Description |
|------|------|------|
| WebSocket Connection | ✅ Completed | Stable connection to Discord Gateway |
| Heartbeat Mechanism | ✅ Completed | Fixed at 60-second intervals |
| Message Filtering | ✅ Completed | Only displays messages from specified channels |
| Channel Name Resolution | ✅ Completed | Retrieves readable channel names from IDs |
| Message Content Retrieval | ✅ Completed | Support for retrieving from regular messages, embeds, and attachments |
| Keyword Filtering | ✅ Completed | Trading signal keyword detection based on configuration |
| Colored Terminal Output | ✅ Completed | Improved log readability |
| REST API Toggle | ✅ Completed | Option to use REST API for detailed information |
| User Message Identification | ✅ Completed | Distinguishes between self and others' messages |
| Message Latency Detection | ✅ Completed | Measures message processing time |
| Enhanced Error Handling | 🚧 In Progress | Need more robust error recovery mechanisms |

### Signal Parsing Module

| Feature | Status | Description |
|------|------|------|
| Basic Keyword Matching | ✅ Completed | Detects trading signal keywords |
| Structured Signal Extraction | 🚧 Planned | Converts messages to standard trading instructions |
| Multi-source Adaptation | 🚧 Planned | Support for different trading signal source formats |

### Trade Execution Module

| Feature | Status | Description |
|------|------|------|
| Paper Trading Interface | 🚧 Planned | Simulated trading system for testing |
| Broker API Integration | 🚧 Planned | Connection to actual broker APIs and trade execution |
| Multi-broker Adapters | 🚧 Planned | Support for multiple trading platforms |

### Risk Management Module

| Feature | Status | Description |
|------|------|------|
| Basic Capital Management | 🚧 Planned | Controls the proportion of capital per trade |
| Stop-Loss/Take-Profit Strategies | 🚧 Planned | Automatically sets stop-loss and take-profit levels |
| Trading Restriction Rules | 🚧 Planned | Prevents excessive trading and risk accumulation |

### System and Infrastructure

| Feature | Status | Description |
|------|------|------|
| Configuration Management | ✅ Completed | YAML configuration system, supports command-line parameters |
| Logging System | ✅ Completed | Basic logging functionality |
| Notification System | ✅ Completed | Support for desktop and console notifications |
| Unit Tests | 🚧 Planned | Test cases for various modules |
| Complete Documentation | 🚧 In Progress | Code comments and usage instructions |

### Recent Updates (2025-04-06)

1. **Discord Listener Enhancements**:
   - Implemented channel filtering functionality, now only displaying messages from channels in the monitoring list
   - Added caching and display of channel names and server names
   - Optimized heartbeat mechanism, fixed at 60-second intervals
   - Improved message content retrieval reliability

2. **Pending Issues**:
   - Optimize reconnection logic, enhance stability
   - Further improve message parsing and signal extraction
   - Add more test cases

## Risk Disclaimer

This software is for educational and research purposes only. Use of this tool for actual trading is at your own risk. The developers are not responsible for any trading decisions or results.

## License

[MIT License](LICENSE) 