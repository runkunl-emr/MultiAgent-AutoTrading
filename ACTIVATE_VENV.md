# How to Activate Virtual Environment on Windows

## Problem
PowerShell blocks script execution by default for security. You're seeing:
```
running scripts is disabled on this system
```

## Solutions

### Option 1: Change Execution Policy (Recommended - One Time Setup)

Open PowerShell as Administrator and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again:
```powershell
.\venv\Scripts\Activate.ps1
```

**What this does:**
- `RemoteSigned`: Allows local scripts to run, but downloaded scripts need to be signed
- `CurrentUser`: Only affects your user account (safer than system-wide)

### Option 2: Bypass for Current Session Only

Run this command first (no admin needed):
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

Then activate:
```powershell
.\venv\Scripts\Activate.ps1
```

**Note:** This only works for the current PowerShell session.

### Option 3: Use Command Prompt Instead (No Policy Issues)

1. Open **Command Prompt** (CMD) instead of PowerShell
2. Navigate to your project:
   ```cmd
   cd C:\Users\Xboy1\OneDrive\Documents\MultiAgent-AutoTrading-master
   ```
3. Activate:
   ```cmd
   venv\Scripts\activate.bat
   ```

### Option 4: Use Python Directly (Skip Activation)

You can also run Python directly from the virtual environment without activating:

```powershell
.\venv\Scripts\python.exe run_discord_monitor.py --config config/discord_config.yaml
```

Or install packages:
```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Recommended: Option 1

For long-term use, I recommend **Option 1** - it's a one-time setup that makes your life easier.

## After Activation

Once activated, you'll see `(venv)` at the start of your prompt:
```
(venv) PS C:\Users\Xboy1\OneDrive\Documents\MultiAgent-AutoTrading-master>
```

Then you can run:
```powershell
pip install -r requirements.txt
python run_discord_monitor.py --config config/discord_config.yaml
```

