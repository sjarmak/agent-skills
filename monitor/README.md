# Agent Driver Monitor

Real-time CPU and network monitoring for AI coding agents (Cursor, Copilot, Gemini, Codex).

## Usage

### macOS / Linux

```bash
# Start monitoring
bash collect.sh &

# Open dashboard (auto-refreshes every 2s)
open monitor.html
```

### Windows

```powershell
# Start monitoring
Start-Process powershell -ArgumentList "-File collect.ps1" -WindowStyle Hidden

# Open dashboard
start monitor.html
```

### Stop Monitoring

```bash
pkill -f collect.sh    # macOS/Linux
```

## Requirements

- **macOS/Linux**: Bash, Python 3
- **Windows**: PowerShell 5.0+
