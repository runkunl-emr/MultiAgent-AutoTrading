---
name: ai-summary
description: Specialized knowledge of the AI-powered Discord message summarization system (OpenAI/Anthropic).
---

# AI Summary System

The project includes an AI-powered summary system for Discord messages.

## Key Components
- `summarize_user_messages.py`: Main script for generating summaries.
- `daily_summary.py`: Orchestrates daily summary generation for multiple users.
- `AISummarizer`: A class that interacts with OpenAI/Anthropic APIs.

## Usage
- Requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.
- Can be run via command line with various flags for channel, user, and output format.

## When to Use
- Use this skill when troubleshooting summary generation or modifying the AI prompts.
- Use this when setting up automation for daily market insights.
