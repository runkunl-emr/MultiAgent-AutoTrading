---
name: config-management
description: Manages the project's multi-file YAML configuration system and environment variables.
---

# Configuration Management

The project uses multiple YAML files for configuration:

1.  `config/config.yaml`: General trading parameters, broker settings, and risk limits.
2.  `config/discord_config.yaml`: Discord bot tokens, channel IDs, and AI summarizer settings.
3.  `config/summary_config.yaml`: Specific settings for the daily summary generation.

## Best Practices
- Always use `config_template.yaml` as a reference.
- Use environment variables for sensitive data (tokens, API keys) when possible.
- The `config.py` module handles loading and merging these configurations.

## When to Use
- Use this skill when the user asks to change bot settings, tokens, or alert channels.
- Use this when adding new configuration fields to ensure they are properly loaded.
