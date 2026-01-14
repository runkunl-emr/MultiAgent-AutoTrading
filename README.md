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

## Documentation

Detailed documentation can be found in the `docs/` directory:
- [Design Document](docs/DESIGN.md): System architecture and requirements.
- [Discord Integration](docs/DISCORD_INTEGRATION.md): Various approaches to Discord connectivity.
- [Summary Guide](docs/SUMMARY_GUIDE.md): Using the historical message analysis and AI summary features.
- [PowerShell Reference](docs/POWERSHELL_COMMANDS.md): Guide for Windows users.

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/quant_trading_bot.git
cd quant_trading_bot
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# .\venv\Scripts\activate # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the template configuration file:
   ```bash
   cp config/discord_config_template.yaml config/discord_config.yaml
   ```

2. Edit the configuration file with your Discord token and monitored channel IDs. You can get your token from the browser's Developer Tools (Network tab -> Authorization header).

## Running

### Discord Monitor (Standalone)
To just monitor Discord and log signals without execution:
```bash
python run_discord_monitor.py --config config/discord_config.yaml
```

### Full Trading Bot
To run the full orchestrator (Parsing -> Risk -> Execution):
```bash
python main.py --config config/config.yaml
```

Options:
- `--dry-run`: Enable paper trading mode (no real trades).
- `--log-level DEBUG`: Show detailed debug logs.

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
| Structured Signal Extraction | ✅ Completed | Support for English and Chinese alert formats |
| Multi-source Adaptation | ✅ Completed | Parser factory for multiple signal formats |

### Trade Execution Module

| Feature | Status | Description |
|------|------|------|
| Paper Trading Interface | ✅ Completed | Simulated trading system with position tracking |
| Broker API Integration | 🚧 Planned | Connection to actual broker APIs (IBKR, MooMoo in progress) |
| Multi-broker Adapters | 🚧 In Progress | Broker adapter interface and factory implemented |

### Risk Management Module

| Feature | Status | Description |
|------|------|------|
| Basic Capital Management | ✅ Completed | Controls position sizing based on account balance |
| Stop-Loss/Take-Profit Strategies | 🚧 Planned | Automatically sets stop-loss and take-profit levels |
| Trading Restriction Rules | ✅ Completed | Daily loss limits, max positions, and blacklists |

### System and Infrastructure

| Feature | Status | Description |
|------|------|------|
| Configuration Management | ✅ Completed | YAML configuration system, supports command-line parameters |
| Logging System | ✅ Completed | Context-aware logging with correlation IDs |
| Notification System | ✅ Completed | Support for Mac system and Console notifications |
| Unit Tests | ✅ Completed | Functional test suite for parsing and execution |
| Complete Documentation | 🚧 In Progress | Ongoing documentation of modules and API |

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