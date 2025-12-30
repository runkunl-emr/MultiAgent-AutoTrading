# AI-Powered Daily Summary Guide

This guide explains how to set up AI-powered daily summaries of stock market messages.

## Features

- 🤖 **AI Summarization**: Uses OpenAI or Anthropic to generate intelligent summaries
- 📊 **Daily Reports**: Automated daily summaries of trading insights
- 📈 **Structured Analysis**: Executive summary, key themes, stock analysis, trading signals
- 💡 **Action Items**: Clear takeaways and recommendations

## Setup

### 1. Install AI Libraries

Choose one or both:

```bash
# For OpenAI (GPT-4, GPT-3.5)
pip install openai

# For Anthropic (Claude)
pip install anthropic
```

### 2. Configure API Key

#### Option A: Environment Variable (Recommended)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Windows CMD
set OPENAI_API_KEY=your-api-key-here

# Mac/Linux
export OPENAI_API_KEY="your-api-key-here"
```

#### Option B: Config File

Edit `config/discord_config.yaml`:

```yaml
ai:
  enabled: true
  provider: "openai"  # or "anthropic"
  api_key: "your-api-key-here"  # Optional if using env var
```

## Usage

### Basic AI Summary

```bash
python summarize_user_messages.py \
  --channel "1447887470434848820" \
  --user "vordinkkk" \
  --ai \
  --output summary.txt
```

### With API Key

```bash
python summarize_user_messages.py \
  --channel "1447887470434848820" \
  --user "vordinkkk" \
  --ai \
  --ai-key "your-api-key" \
  --ai-provider openai \
  --output summary.txt
```

### Daily Summary Script

Automatically generate summaries for all configured users:

```bash
python daily_summary.py
```

This will:
- Read `user_filters` from config
- Generate AI summaries for each user
- Save to `summaries/` directory with date stamps

## Daily Automation

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 6:00 AM
4. Action: Start a program
5. Program: `python`
6. Arguments: `daily_summary.py --config config/discord_config.yaml`
7. Start in: `C:\path\to\MultiAgent-AutoTrading-master`

### Linux/Mac Cron

Add to crontab (`crontab -e`):

```bash
# Run daily summary at 6 AM every day
0 6 * * * cd /path/to/MultiAgent-AutoTrading-master && /usr/bin/python3 daily_summary.py >> logs/daily_summary.log 2>&1
```

### Python Script (Cross-platform)

Create `run_daily_summary.py`:

```python
import schedule
import time
import subprocess
import sys

def run_summary():
    subprocess.run([sys.executable, "daily_summary.py"])

# Schedule daily at 6 AM
schedule.every().day.at("06:00").do(run_summary)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Run: `python run_daily_summary.py`

## Output Format

The AI summary includes:

### 1. Executive Summary
Brief overview of trading activity and key insights

### 2. Key Themes
Main topics and strategies discussed

### 3. Stock Analysis
- Bullish/bearish sentiment
- Entry/exit points
- Price targets and stop losses
- Risk assessments

### 4. Trading Signals
Clear buy/sell signals identified

### 5. Market Outlook
Overall market sentiment and predictions

### 6. Action Items
Key takeaways and recommended actions

## Example Output

```
================================================================================
AI-GENERATED DAILY SUMMARY
================================================================================

**Executive Summary**
User vordinkkk posted 15 stock-related messages today, focusing primarily on 
tech stocks (AAPL, TSLA, NVDA) with a bullish outlook. Key themes include 
earnings expectations and technical analysis.

**Key Themes**
- Tech sector momentum
- Earnings season preparation
- Technical breakout patterns

**Stock Analysis**

**AAPL (Apple)**
- Sentiment: Bullish
- Entry Point: $180
- Target: $200
- Stop Loss: $175
- Risk: Medium
- Analysis: User expects strong earnings beat...

**TSLA (Tesla)**
- Sentiment: Bullish
- Entry Point: $250
- Target: $280
- Stop Loss: $240
- Risk: High
- Analysis: Technical breakout pattern identified...

**Trading Signals**
1. BUY AAPL at $180, target $200
2. BUY TSLA at $250, target $280
3. Monitor NVDA for entry opportunity

**Market Outlook**
Overall bullish sentiment on tech sector. User expects continued momentum 
through earnings season. Caution advised on high volatility names.

**Action Items**
- Monitor AAPL earnings announcement
- Set alerts for TSLA breakout
- Review NVDA technical levels
```

## Cost Estimation

### OpenAI
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Typical daily summary: ~$0.01-0.05 per summary

### Anthropic
- Claude 3 Haiku: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
- Typical daily summary: ~$0.02-0.08 per summary

## Advanced Configuration

### Custom Prompts

Edit `summarize_user_messages.py` to customize the AI prompt in `AISummarizer.generate_daily_summary()`.

### Multiple Providers

You can switch providers:

```bash
# Use OpenAI
--ai-provider openai

# Use Anthropic
--ai-provider anthropic
```

### Model Selection

Edit the model in `AISummarizer` class:
- OpenAI: `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-haiku-20240307`, `claude-3-opus-20240229`

## Troubleshooting

### "AI API key not found"
- Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variable
- Or add `ai.api_key` to config file
- Or use `--ai-key` parameter

### "OpenAI library not installed"
```bash
pip install openai
```

### "Error generating AI summary"
- Check API key is valid
- Check you have API credits
- Verify internet connection
- Check rate limits

### High Costs
- Use cheaper models (gpt-4o-mini, claude-3-haiku)
- Reduce `--max` messages
- Limit to most recent messages only

## Integration with Main Bot

The daily summary script works independently but can be integrated:

1. **Scheduled**: Run daily via cron/task scheduler
2. **On-demand**: Run manually when needed
3. **Combined**: Use alongside real-time monitoring bot

## Next Steps

- Set up daily automation
- Customize AI prompts for your needs
- Add email/Slack notifications
- Create web dashboard for summaries
- Add database storage for historical analysis

