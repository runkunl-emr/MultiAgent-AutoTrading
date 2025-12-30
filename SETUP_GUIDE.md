# Discord Message Forwarding Bot - Setup Guide

This guide will help you set up and run the Discord message forwarding bot locally.

## What This Bot Does

- **Monitors** messages from specified Discord channels
- **Forwards** those messages to a destination channel (optional)
- **Detects** trading signals based on keywords
- **Logs** all activity

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Discord User Token** (see how to get it below)
3. **Channel IDs** for:
   - Source channels (channels to monitor)
   - Destination channel (where messages will be forwarded - optional)

## Step 1: Get Your Discord Token

### Option A: Using Browser Developer Tools (Recommended)

1. Open Discord in your web browser (Chrome, Firefox, Edge)
2. Press `F12` to open Developer Tools
3. Go to the **Network** tab
4. In Discord, send a message or perform any action
5. Look for a request to `discord.com/api` in the Network tab
6. Click on it and go to **Headers**
7. Find the `Authorization` header
8. Copy the token (it will look like: `MTk...` or `OD...`)

⚠️ **IMPORTANT**: Never share your token with anyone! It gives full access to your Discord account.

### Option B: Using Discord Developer Mode

1. Open Discord Settings
2. Go to **Advanced** → Enable **Developer Mode**
3. Right-click on any channel → **Copy Channel ID**
4. For token, you'll still need to use Option A

## Step 2: Get Channel IDs

1. Enable **Developer Mode** in Discord (Settings → Advanced → Developer Mode)
2. Right-click on the channel you want to monitor → **Copy Channel ID**
3. Repeat for the destination channel (if you want to forward messages)

## Step 3: Install Dependencies

1. Open a terminal/command prompt in the project directory
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```
4. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Configure the Bot

1. Copy the configuration template:
   ```bash
   # Windows
   copy config\discord_config_template.yaml config\discord_config.yaml
   
   # Mac/Linux
   cp config/discord_config_template.yaml config/discord_config.yaml
   ```

2. Edit `config/discord_config.yaml` and fill in:
   - `token`: Your Discord user token
   - `channel_ids`: List of channel IDs to monitor (source channels)
   - `destination_channel_id`: Channel ID where messages will be forwarded (optional - leave empty if not forwarding)

   Example configuration:
   ```yaml
   discord:
     token: "YOUR_TOKEN_HERE"
     channel_ids:
       - "1234567890123456789"  # Source channel 1
       - "9876543210987654321"  # Source channel 2
     destination_channel_id: "1111111111111111111"  # Destination channel (optional)
   ```

## Step 5: Run the Bot

### Option A: Using the Main Script

```bash
python run_discord_monitor.py --config config/discord_config.yaml
```

### Option B: Interactive Mode (Recommended for First Time)

This will prompt you to enter your token and channel IDs:

```bash
python run_discord_monitor.py --interactive
```

### Option C: Command Line Arguments

```bash
python run_discord_monitor.py --token YOUR_TOKEN --channel SOURCE_CHANNEL_ID --channel ANOTHER_CHANNEL_ID
```

## Step 6: Verify It's Working

When the bot starts, you should see:
- ✅ Connection confirmation
- ✅ List of monitored channels
- ✅ Destination channel (if configured)
- ✅ "Waiting for messages..." message

When a message arrives in a monitored channel:
- The message will be displayed in the console
- If forwarding is enabled, you'll see "✓ Message forwarded to destination channel"
- Messages are also logged to `logs/trading_signals.log`

## Troubleshooting

### Error: "Authentication failed" or "Invalid token"
- Make sure you copied the entire token correctly
- Token should not have quotes around it in the config file
- Try getting a fresh token using the browser method

### Error: "No access to channel"
- Make sure your Discord account has access to the channel
- Verify the channel ID is correct
- The bot needs to be able to read from source channels and write to destination channel

### Messages not forwarding
- Check that `destination_channel_id` is set in config
- Verify the destination channel ID is correct
- Make sure your account has permission to send messages in the destination channel
- Check the console for error messages

### Bot stops working after a while
- Discord may rate limit requests
- The bot will attempt to reconnect automatically
- Check `logs/discord_monitor.log` for detailed error information

## Configuration Options

### Full Configuration Example

```yaml
discord:
  token: "YOUR_TOKEN"
  channel_ids:
    - "SOURCE_CHANNEL_ID_1"
    - "SOURCE_CHANNEL_ID_2"
  destination_channel_id: "DESTINATION_CHANNEL_ID"  # Optional
  signal_keywords:
    - buy
    - sell
    - signal

notification:
  enabled: true
  sound: "Submarine"

logging:
  level: "INFO"
  file: "logs/discord_monitor.log"
  signal_file: "logs/trading_signals.log"
```

## Security Notes

1. **Never commit your token to Git** - Add `config/discord_config.yaml` to `.gitignore`
2. **Use environment variables** for tokens in production
3. **Keep your token secret** - Anyone with your token can access your Discord account
4. **Regularly rotate tokens** if you suspect it's been compromised

## Stopping the Bot

Press `Ctrl+C` in the terminal to stop the bot gracefully.

## Next Steps

- Customize signal keywords in the config file
- Adjust logging levels for more/less detail
- Set up notifications for trading signals
- Review logs in the `logs/` directory

## Need Help?

- Check the logs in `logs/discord_monitor.log`
- Review error messages in the console
- Verify all IDs and tokens are correct
- Make sure you have proper Discord permissions

