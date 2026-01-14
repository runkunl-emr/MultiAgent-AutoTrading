---
name: coding-standards
description: Enforces PEP 8, type hints, and specific logging patterns for the MultiAgent-AutoTrading project.
---

# Coding Standards

- **Type Hints**: Use type hints for all function signatures.
- **Style**: Follow PEP 8 style guide.
- **Testing**: Ensure all new features are accompanied by tests in `test_bot.py`.
- **Logging**: Log important events using the custom logger from `utils.logging`.
- **Error Handling**: Handle exceptions gracefully using the retry and circuit breaker patterns where appropriate.

## When to Use
- Use this skill during code reviews or when generating new code.
- Use this when refactoring existing modules to maintain consistency.
