# User Message and AI Summary Guide

This guide explains how to use the historical message analysis and AI-powered summarization features.

## 1. Historical Message Analysis

The `summarize_user_messages.py` script analyzes all messages from a specific user in a Discord channel and summarizes their stock market insights.

### Features
- ✅ Fetches historical messages from a Discord channel
- ✅ Filters messages by username
- ✅ Identifies stock market-related content
- ✅ Extracts mentioned tickers/symbols
- ✅ Generates a summary report (Text + JSON)

### Usage
```bash
python summarize_user_messages.py --channel CHANNEL_ID --user USERNAME --output summary.txt
```

### Full Example
```bash
python summarize_user_messages.py \
  --config config/discord_config.yaml \
  --channel "1447887470434848820" \
  --user "vordinkkk" \
  --max 2000 \
  --output summaries/vordinkkk_summary.txt
```

---

## 2. AI-Powered Daily Summaries

You can use OpenAI or Anthropic to generate intelligent daily summaries of trading insights.

### Setup
1. **Install AI Libraries**:
   ```bash
   pip install openai anthropic
   ```

2. **Configure API Key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Usage
```bash
python summarize_user_messages.py \
  --channel "1447887470434848820" \
  --user "vordinkkk" \
  --ai \
  --output summary.txt
```

### Automated Daily Summaries
Automatically generate summaries for all configured users:
```bash
python daily_summary.py
```
This will:
- Read `user_filters` from config
- Generate AI summaries for each user
- Save to `summaries/` directory with date stamps

---

## 3. Output Format

The summary includes:
1. **Executive Summary**: Brief overview of trading activity.
2. **Key Themes**: Main topics and strategies discussed.
3. **Stock Analysis**: Sentiment, entry/exit points, and price targets.
4. **Trading Signals**: Clear buy/sell signals identified.
5. **Market Outlook**: Overall market sentiment.
6. **Action Items**: Key takeaways and recommendations.
