# PowerShell Command Reference

## Running Python Scripts in PowerShell

### Option 1: Single Line (Easiest)

```powershell
python summarize_user_messages.py --channel "1444092443724353546" --user "alex.0692" --ai --output summary.txt
```

### Option 2: Multi-line with Backticks (PowerShell Style)

```powershell
python summarize_user_messages.py `
  --channel "1444092443724353546" `
  --user "alex.0692" `
  --ai `
  --output summary.txt
```

**Note**: PowerShell uses backticks `` ` `` (not backslashes `\`) for line continuation.

### Option 3: Using Array (For Complex Commands)

```powershell
$args = @(
    "summarize_user_messages.py",
    "--channel", "1444092443724353546",
    "--user", "alex.0692",
    "--ai",
    "--output", "summary.txt"
)
python $args
```

## Common Commands

### Generate AI Summary

```powershell
python summarize_user_messages.py --channel "1444092443724353546" --user "alex.0692" --ai --output summary.txt
```

### Daily Summary

```powershell
python daily_summary.py
```

### Run Discord Monitor

```powershell
python run_discord_monitor.py --config config/discord_config.yaml
```

## Setting Environment Variables

### Temporary (Current Session)

```powershell
$env:GEMINI_API_KEY="your-api-key-here"
$env:OPENAI_API_KEY="your-api-key-here"
```

### Permanent (User Level)

```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-api-key-here", "User")
```

Then restart PowerShell for changes to take effect.

## Quick Reference

| Bash/Linux | PowerShell |
|------------|------------|
| `\` (line continuation) | `` ` `` (backtick) |
| `export VAR=value` | `$env:VAR="value"` |
| `&&` | `;` or separate commands |
| `./script.sh` | `.\script.ps1` or `python script.py` |

