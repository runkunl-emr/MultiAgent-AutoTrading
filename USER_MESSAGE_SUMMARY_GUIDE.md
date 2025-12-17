# User Message Summary Guide

This script analyzes all messages from a specific user in a Discord channel and summarizes their stock market insights.

## Features

- ✅ Fetches historical messages from a Discord channel
- ✅ Filters messages by username
- ✅ Identifies stock market-related content
- ✅ Extracts mentioned tickers/symbols
- ✅ Generates a summary report
- ✅ Saves results to file (text + JSON)

## Usage

### Basic Usage

```bash
python summarize_user_messages.py --channel CHANNEL_ID --user USERNAME
```

### With Output File

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

## Parameters

- `--config, -c`: Configuration file path (default: `config/discord_config.yaml`)
- `--channel, -ch`: **Required** - Channel ID to fetch messages from
- `--user, -u`: **Required** - Username to filter messages by
- `--max, -m`: Maximum messages to fetch (default: 1000)
- `--output, -o`: Output file path (optional, prints to console if not specified)

## Output

The script generates:

1. **Text Summary** (`.txt` file):
   - Total messages analyzed
   - Stock-related message count
   - All tickers mentioned
   - Date range of messages
   - Key messages (first 20)

2. **JSON Data** (`.json` file):
   - Complete structured data
   - All stock-related messages
   - Timestamps and message IDs
   - Easy to process programmatically

## Example Output

```
================================================================================
STOCK MARKET MESSAGE SUMMARY
================================================================================
User: vordinkkk
Channel: trading-signals
Total Messages Analyzed: 150
Stock-Related Messages: 45

Tickers Mentioned (12):
AAPL, TSLA, NVDA, MSFT, GOOGL, AMZN, META, NFLX, AMD, INTC, QQQ, SPY

Date Range:
  Earliest: 2024-01-15T10:30:00+00:00
  Latest: 2024-01-20T15:45:00+00:00

================================================================================
KEY MESSAGES:
================================================================================

[1] 2024-01-20T15:45:00+00:00
Buy signal for $AAPL at $180. Target $200. Stop loss $175...

[2] 2024-01-19T14:20:00+00:00
TSLA looking bullish. Entry at $250, target $280...
```

## Stock Market Detection

The script identifies stock-related messages by looking for keywords like:
- Stock/trading terms: stock, ticker, buy, sell, long, short
- Market terms: bullish, bearish, entry, exit, target
- Financial terms: earnings, revenue, profit, valuation
- Crypto terms: bitcoin, btc, eth, crypto
- And more...

## Limitations

1. **Rate Limits**: Discord API has rate limits. Fetching many messages may take time.
2. **Message History**: Can only fetch messages your account has access to
3. **User Token**: Requires a valid Discord user token with channel access
4. **Pagination**: Fetches messages in batches of 100

## Troubleshooting

### "No messages found"
- Verify the username is correct (case-sensitive)
- Check that your token has access to the channel
- Ensure the user has posted messages in that channel

### "Error fetching messages"
- Check your Discord token is valid
- Verify you have permission to read the channel
- Check rate limits (wait a few minutes and try again)

### Rate Limit Errors
- Reduce `--max` parameter
- Wait a few minutes between runs
- Discord limits: ~50 requests per second

## Advanced Usage

### Analyze Multiple Users

Create a script to analyze multiple users:

```bash
#!/bin/bash
python summarize_user_messages.py --channel CHANNEL_ID --user user1 --output user1.txt
python summarize_user_messages.py --channel CHANNEL_ID --user user2 --output user2.txt
python summarize_user_messages.py --channel CHANNEL_ID --user user3 --output user3.txt
```

### Process JSON Output

The JSON output can be processed with other tools:

```python
import json

with open('summary.json', 'r') as f:
    data = json.load(f)
    
print(f"Found {len(data['tickers_mentioned'])} tickers")
for ticker in data['tickers_mentioned']:
    print(f"  - {ticker}")
```

## Integration with Main Bot

This script works independently from the main monitoring bot (`run_discord_monitor.py`). You can:

1. Run it on-demand to analyze historical data
2. Schedule it (cron/task scheduler) for regular summaries
3. Use it alongside the real-time monitoring bot

## Next Steps

Consider enhancing the script with:
- AI-powered summarization (OpenAI API)
- Sentiment analysis
- Price tracking integration
- Database storage for historical analysis
- Web dashboard for visualization

