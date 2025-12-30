# Quick Start Guide

## What You Need to Change/Get

### 1. Discord User Token
- Open Discord in browser → Press F12 → Network tab → Find any Discord API request → Copy `Authorization` header value
- **Never share this token!**

### 2. Channel IDs
- Enable Developer Mode in Discord (Settings → Advanced)
- Right-click channel → Copy Channel ID
- Get IDs for:
  - **Source channels** (channels to monitor)
  - **Destination channel** (where to forward messages - optional)

### 3. Configuration File
Create `config/discord_config.yaml`:
```yaml
discord:
  token: "YOUR_TOKEN_HERE"
  channel_ids:
    - "SOURCE_CHANNEL_ID_1"
    - "SOURCE_CHANNEL_ID_2"
  destination_channel_id: "DESTINATION_CHANNEL_ID"  # Optional - leave empty if not forwarding
```

## How to Run Locally

### Step 1: Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (Mac/Linux)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure
```bash
# Copy template
copy config\discord_config_template.yaml config\discord_config.yaml  # Windows
cp config/discord_config_template.yaml config/discord_config.yaml     # Mac/Linux

# Edit config/discord_config.yaml with your token and channel IDs
```

### Step 3: Run
```bash
# Option 1: Using config file
python run_discord_monitor.py --config config/discord_config.yaml

# Option 2: Interactive mode (prompts for input)
python run_discord_monitor.py --interactive

# Option 3: Command line
python run_discord_monitor.py --token YOUR_TOKEN --channel CHANNEL_ID
```

## What Happens

1. Bot connects to Discord
2. Monitors specified source channels
3. When a message arrives:
   - Displays it in console
   - Forwards to destination channel (if configured)
   - Logs to `logs/trading_signals.log`
4. Detects trading signals based on keywords

## Stop the Bot
Press `Ctrl+C` in the terminal

## Troubleshooting

- **"Authentication failed"** → Check your token is correct
- **"No access to channel"** → Verify channel IDs and permissions
- **Messages not forwarding** → Check destination_channel_id is set and correct

See `SETUP_GUIDE.md` for detailed instructions.

