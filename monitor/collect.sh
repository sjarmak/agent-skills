#!/bin/bash
# Agent Driver Monitor - Data Collection Script (macOS & Linux)
# Tracks CPU per agent + network activity attributed to running agents

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$SCRIPT_DIR/monitor.html"

HISTORY_FILE="/tmp/agent_monitor_history.json"
NET_HISTORY_FILE="/tmp/agent_monitor_net_history.json"
PREV_NET_FILE="/tmp/agent_monitor_prev_net.json"

# Detect OS
OS_TYPE="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
fi

# Function to get network bytes (cross-platform)
get_network_bytes() {
    if [ "$OS_TYPE" = "macos" ]; then
        # macOS: use netstat -ib
        local net_stats=$(netstat -ib 2>/dev/null | grep -E '^en0\s' | head -1)
        local net_in=$(echo "$net_stats" | awk '{print $7}')
        local net_out=$(echo "$net_stats" | awk '{print $10}')
        echo "${net_in:-0} ${net_out:-0}"
    elif [ "$OS_TYPE" = "linux" ]; then
        # Linux: use /proc/net/dev (try common interfaces)
        local interface=""
        for iface in eth0 ens33 ens18 enp0s3 wlan0 wlp2s0; do
            if grep -q "$iface:" /proc/net/dev 2>/dev/null; then
                interface="$iface"
                break
            fi
        done
        if [ -n "$interface" ]; then
            local stats=$(grep "$interface:" /proc/net/dev | awk '{print $2, $10}')
            echo "${stats:-0 0}"
        else
            echo "0 0"
        fi
    else
        echo "0 0"
    fi
}

# Initialize history files
echo '{"labels":[],"cursor":[],"copilot":[],"gemini":[],"codex":[]}' > "$HISTORY_FILE"
echo '{"labels":[],"cursor":[],"copilot":[],"gemini":[],"codex":[]}' > "$NET_HISTORY_FILE"
echo '{"total":0,"time":0}' > "$PREV_NET_FILE"

echo "Agent Monitor started (OS: $OS_TYPE)"

while true; do
    time_label=$(date +"%H:%M:%S")
    
    # Detect agents and count how many are running
    agents_running=0
    
    # Cursor agent
    cursor_data=$(ps aux | grep -E '\sagent\s' | grep -v grep | head -1)
    if [ -n "$cursor_data" ]; then
        cursor_running="true"
        cursor_cpu=$(echo "$cursor_data" | awk '{print $3}')
        ((agents_running++))
    else
        cursor_running="false"
        cursor_cpu="0"
    fi
    
    # Copilot
    copilot_data=$(ps aux | grep -iE 'copilot' | grep -v grep | head -1)
    if [ -n "$copilot_data" ]; then
        copilot_running="true"
        copilot_cpu=$(echo "$copilot_data" | awk '{print $3}')
        ((agents_running++))
    else
        copilot_running="false"
        copilot_cpu="0"
    fi
    
    # Gemini
    gemini_data=$(ps aux | grep -E 'node.*gemini' | grep -v grep | head -1)
    if [ -n "$gemini_data" ]; then
        gemini_running="true"
        gemini_cpu=$(echo "$gemini_data" | awk '{print $3}')
        ((agents_running++))
    else
        gemini_running="false"
        gemini_cpu="0"
    fi
    
    # Codex
    codex_data=$(ps aux | grep -iE 'codex|codex-cli' | grep -v grep | head -1)
    if [ -n "$codex_data" ]; then
        codex_running="true"
        codex_cpu=$(echo "$codex_data" | awk '{print $3}')
        ((agents_running++))
    else
        codex_running="false"
        codex_cpu="0"
    fi
    
    # Get network bytes
    read current_net_in current_net_out <<< $(get_network_bytes)
    current_total=$((${current_net_in:-0} + ${current_net_out:-0}))
    
    # Calculate network and attribute to running agents
    python3 > /dev/null << PYEOF
import json
import time

# CPU History
try:
    with open("$HISTORY_FILE", "r") as f:
        history = json.load(f)
except:
    history = {"labels":[],"cursor":[],"copilot":[],"gemini":[],"codex":[]}

history["labels"].append("$time_label")
history["cursor"].append($cursor_cpu)
history["copilot"].append($copilot_cpu)
history["gemini"].append($gemini_cpu)
history["codex"].append($codex_cpu)

for key in history:
    history[key] = history[key][-60:]

with open("$HISTORY_FILE", "w") as f:
    json.dump(history, f)

# Network calculation - attribute to running agents
try:
    with open("$PREV_NET_FILE", "r") as f:
        prev = json.load(f)
except:
    prev = {"total": 0, "time": 0}

current_time = time.time()
time_diff = current_time - prev.get("time", current_time - 2)
if time_diff < 0.5:
    time_diff = 2

current_total = $current_total
prev_total = prev.get("total", current_total)

# Total network rate in KB/s
total_rate = max(0, (current_total - prev_total) / 1024 / time_diff) if prev_total > 0 else 0

# Attribute network to running agents
agents_running = $agents_running
cursor_running = "$cursor_running" == "true"
copilot_running = "$copilot_running" == "true"  
gemini_running = "$gemini_running" == "true"
codex_running = "$codex_running" == "true"

if agents_running > 0:
    per_agent_rate = total_rate / agents_running
    cursor_net = per_agent_rate if cursor_running else 0
    copilot_net = per_agent_rate if copilot_running else 0
    gemini_net = per_agent_rate if gemini_running else 0
    codex_net = per_agent_rate if codex_running else 0
else:
    cursor_net = copilot_net = gemini_net = codex_net = 0

with open("$PREV_NET_FILE", "w") as f:
    json.dump({
        "total": current_total, 
        "time": current_time,
        "cursor_net": round(cursor_net, 1),
        "copilot_net": round(copilot_net, 1),
        "gemini_net": round(gemini_net, 1),
        "codex_net": round(codex_net, 1)
    }, f)

# Network History per agent
try:
    with open("$NET_HISTORY_FILE", "r") as f:
        net_history = json.load(f)
except:
    net_history = {"labels":[],"cursor":[],"copilot":[],"gemini":[],"codex":[]}

net_history["labels"].append("$time_label")
net_history["cursor"].append(round(cursor_net, 1))
net_history["copilot"].append(round(copilot_net, 1))
net_history["gemini"].append(round(gemini_net, 1))
net_history["codex"].append(round(codex_net, 1))

for key in net_history:
    net_history[key] = net_history[key][-60:]

with open("$NET_HISTORY_FILE", "w") as f:
    json.dump(net_history, f)
PYEOF
    
    # Read values
    history_json=$(cat "$HISTORY_FILE")
    net_history_json=$(cat "$NET_HISTORY_FILE")
    
    cursor_net=$(python3 -c "import json; d=json.load(open('$PREV_NET_FILE')); print(d.get('cursor_net',0))" 2>/dev/null || echo "0")
    copilot_net=$(python3 -c "import json; d=json.load(open('$PREV_NET_FILE')); print(d.get('copilot_net',0))" 2>/dev/null || echo "0")
    gemini_net=$(python3 -c "import json; d=json.load(open('$PREV_NET_FILE')); print(d.get('gemini_net',0))" 2>/dev/null || echo "0")
    codex_net=$(python3 -c "import json; d=json.load(open('$PREV_NET_FILE')); print(d.get('codex_net',0))" 2>/dev/null || echo "0")
    
    # CSS classes
    cursor_class=""; copilot_class=""; gemini_class=""; codex_class=""
    [ "$cursor_running" = "true" ] && cursor_class="running"
    [ "$copilot_running" = "true" ] && copilot_class="running"
    [ "$gemini_running" = "true" ] && gemini_class="running"
    [ "$codex_running" = "true" ] && codex_class="running"
    
    # Write HTML
    cat > "$OUTPUT_FILE" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="2">
    <title>Agent Driver Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #e0e0e0; padding: 20px; opacity: 0; animation: fadeIn 0.15s ease-out forwards; }
        @keyframes fadeIn { to { opacity: 1; } }
        .container { max-width: 1400px; margin: 0 auto; }
        header { margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #333; }
        h1 { font-size: 1.8rem; margin-bottom: 8px; color: #fff; }
        .last-update { color: #888; font-size: 0.85rem; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .status-card { background: #2a2a2a; border-radius: 8px; padding: 15px; border: 1px solid #333; }
        .status-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; background: #555; }
        .status-dot.running { background: #4caf50; box-shadow: 0 0 8px #4caf50; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .status-name { font-size: 1.1rem; font-weight: 600; text-transform: capitalize; }
        .metrics { display: flex; gap: 20px; }
        .metric { flex: 1; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: #fff; }
        .metric-value.cpu { color: #2196f3; }
        .metric-value.net { color: #4caf50; }
        .metric-label { font-size: 0.75rem; color: #888; margin-top: 2px; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }
        .chart-container { background: #2a2a2a; border-radius: 8px; padding: 15px; border: 1px solid #333; height: 280px; }
        .chart-container h2 { font-size: 0.9rem; color: #fff; margin-bottom: 10px; }
        canvas { max-height: 220px; }
        .note { font-size: 0.75rem; color: #666; margin-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Agent Driver Monitor</h1>
            <div class="last-update">Last update: $time_label • OS: $OS_TYPE (auto-refreshes every 2s)</div>
        </header>
        
        <div class="status-grid">
            <div class="status-card">
                <div class="status-header">
                    <div class="status-dot $cursor_class"></div>
                    <div class="status-name">Cursor</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value cpu">${cursor_cpu}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value net">${cursor_net} KB/s</div>
                        <div class="metric-label">Network</div>
                    </div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header">
                    <div class="status-dot $copilot_class"></div>
                    <div class="status-name">Copilot</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value cpu">${copilot_cpu}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value net">${copilot_net} KB/s</div>
                        <div class="metric-label">Network</div>
                    </div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header">
                    <div class="status-dot $gemini_class"></div>
                    <div class="status-name">Gemini</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value cpu">${gemini_cpu}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value net">${gemini_net} KB/s</div>
                        <div class="metric-label">Network</div>
                    </div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header">
                    <div class="status-dot $codex_class"></div>
                    <div class="status-name">Codex</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value cpu">${codex_cpu}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value net">${codex_net} KB/s</div>
                        <div class="metric-label">Network</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h2>📊 CPU Usage Over Time</h2>
                <canvas id="cpuChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>🌐 Network Per Agent (KB/s)</h2>
                <canvas id="netChart"></canvas>
            </div>
        </div>
        
        <div class="note">Network is attributed to active agents only (split evenly when multiple agents run simultaneously)</div>
    </div>
    
    <script>
        const historyData = $history_json;
        const netHistoryData = $net_history_json;
        
        new Chart(document.getElementById('cpuChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: historyData.labels,
                datasets: [
                    { label: 'Cursor', data: historyData.cursor, borderColor: '#2196f3', tension: 0.4, borderWidth: 2 },
                    { label: 'Copilot', data: historyData.copilot, borderColor: '#4caf50', tension: 0.4, borderWidth: 2 },
                    { label: 'Gemini', data: historyData.gemini, borderColor: '#ff9800', tension: 0.4, borderWidth: 2 },
                    { label: 'Codex', data: historyData.codex, borderColor: '#9c27b0', tension: 0.4, borderWidth: 2 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: {
                    x: { ticks: { color: '#888', maxRotation: 0, maxTicksLimit: 8 }, grid: { color: '#333' } },
                    y: { beginAtZero: true, max: 100, ticks: { color: '#888', callback: v => v + '%' }, grid: { color: '#333' } }
                }
            }
        });
        
        new Chart(document.getElementById('netChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: netHistoryData.labels,
                datasets: [
                    { label: 'Cursor', data: netHistoryData.cursor, borderColor: '#2196f3', backgroundColor: 'rgba(33,150,243,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                    { label: 'Copilot', data: netHistoryData.copilot, borderColor: '#4caf50', backgroundColor: 'rgba(76,175,80,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                    { label: 'Gemini', data: netHistoryData.gemini, borderColor: '#ff9800', backgroundColor: 'rgba(255,152,0,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                    { label: 'Codex', data: netHistoryData.codex, borderColor: '#9c27b0', backgroundColor: 'rgba(156,39,176,0.1)', tension: 0.4, borderWidth: 2, fill: true }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: {
                    x: { ticks: { color: '#888', maxRotation: 0, maxTicksLimit: 8 }, grid: { color: '#333' } },
                    y: { beginAtZero: true, ticks: { color: '#888', callback: v => v + ' KB/s' }, grid: { color: '#333' } }
                }
            }
        });
    </script>
</body>
</html>
HTMLEOF
    
    sleep 2
done
