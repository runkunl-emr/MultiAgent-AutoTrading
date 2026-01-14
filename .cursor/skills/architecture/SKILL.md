---
name: architecture
description: Understands the modular architecture of the MultiAgent-AutoTrading system, from Discord listeners to broker execution.
---

# Project Architecture

The system follows a modular architecture:

1.  **Listener** (`core/listener.py`): Connects to Discord and listens for messages.
2.  **Parser** (`core/parser.py`): Processes raw messages into `TradeSignal` objects.
3.  **Orchestrator** (`core/orchestrator.py`): Coordinates the flow between listener, parser, and executor.
4.  **Risk Guard** (`core/risk_guard.py`): Validates signals against risk parameters.
5.  **Executor** (`core/executor.py`): Executes the trade via an adapter.
6.  **Adapters** (`adapters/`): Handle the actual API calls to brokers (e.g., IBKR, Mock).

## Flow
`Discord -> Listener -> Orchestrator -> Parser -> Orchestrator -> Risk Guard -> Orchestrator -> Executor -> Broker Adapter`

## When to Use
- Use this skill when explaining how the bot components interact.
- Use this when adding new core modules to ensure they fit the flow.
