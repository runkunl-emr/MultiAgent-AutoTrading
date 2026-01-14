---
name: trading-logic
description: Expert in trading signal parsing, execution strategies, and risk management validation.
---

# Trading Logic and Signal Parsing

## Signal Parsing
- Parsers are registered in `ParserFactory`.
- New parsers should implement `can_parse()` and `parse_alert()`.
- Use regex for extracting symbols, prices, and actions (BUY/SELL).

## Trade Execution
- Execution is handled by `TradeExecutor`.
- It supports dry-run mode where no actual trades are placed.
- Always check the `dry_run` flag in configuration.

## Risk Management
- Every trade MUST pass the `RiskGuard`.
- Risk parameters include maximum position size, stop-loss requirements, and daily limits.

## When to Use
- Use this skill when modifying the parsing logic for new Discord alert formats.
- Use this when adjusting risk parameters or adding new broker execution logic.
