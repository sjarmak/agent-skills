# Agent Driver Monitor - Data Collection Script (Windows)
# Tracks CPU per agent + network activity attributed to running agents

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$OUTPUT_FILE = Join-Path $SCRIPT_DIR "monitor.html"
$HISTORY_FILE = "$env:TEMP\agent_monitor_history.json"
$NET_HISTORY_FILE = "$env:TEMP\agent_monitor_net_history.json"
$PREV_NET_FILE = "$env:TEMP\agent_monitor_prev_net.json"

# Initialize history files
@{labels=@();cursor=@();copilot=@();gemini=@();codex=@()} | ConvertTo-Json | Out-File $HISTORY_FILE -Encoding UTF8
@{labels=@();cursor=@();copilot=@();gemini=@();codex=@()} | ConvertTo-Json | Out-File $NET_HISTORY_FILE -Encoding UTF8
@{total=0;time=0} | ConvertTo-Json | Out-File $PREV_NET_FILE -Encoding UTF8

Write-Host "Agent Monitor started (OS: Windows)"

while ($true) {
    $timeLabel = (Get-Date).ToString("HH:mm:ss")
    $agentsRunning = 0
    
    # Detect Cursor agent
    $cursorProc = Get-Process | Where-Object { $_.ProcessName -match 'agent' } | Select-Object -First 1
    if ($cursorProc) {
        $cursorRunning = "true"
        $cursorCpu = [math]::Round((Get-Counter "\Process($($cursorProc.ProcessName))\% Processor Time" -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue / [Environment]::ProcessorCount, 1)
        if (-not $cursorCpu) { $cursorCpu = 0 }
        $agentsRunning++
    } else {
        $cursorRunning = "false"
        $cursorCpu = 0
    }
    
    # Detect Copilot
    $copilotProc = Get-Process | Where-Object { $_.ProcessName -match 'copilot' -or $_.MainWindowTitle -match 'copilot' } | Select-Object -First 1
    if ($copilotProc) {
        $copilotRunning = "true"
        $copilotCpu = [math]::Round((Get-Counter "\Process($($copilotProc.ProcessName))\% Processor Time" -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue / [Environment]::ProcessorCount, 1)
        if (-not $copilotCpu) { $copilotCpu = 0 }
        $agentsRunning++
    } else {
        $copilotRunning = "false"
        $copilotCpu = 0
    }
    
    # Detect Gemini
    $geminiProc = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'gemini' } | Select-Object -First 1
    if ($geminiProc) {
        $geminiRunning = "true"
        $geminiCpu = 0
        $agentsRunning++
    } else {
        $geminiRunning = "false"
        $geminiCpu = 0
    }
    
    # Detect Codex
    $codexProc = Get-Process | Where-Object { $_.ProcessName -match 'codex' } | Select-Object -First 1
    if ($codexProc) {
        $codexRunning = "true"
        $codexCpu = [math]::Round((Get-Counter "\Process($($codexProc.ProcessName))\% Processor Time" -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue / [Environment]::ProcessorCount, 1)
        if (-not $codexCpu) { $codexCpu = 0 }
        $agentsRunning++
    } else {
        $codexRunning = "false"
        $codexCpu = 0
    }
    
    # Get network bytes
    $netAdapter = Get-NetAdapterStatistics | Select-Object -First 1
    $currentNetIn = if ($netAdapter) { $netAdapter.ReceivedBytes } else { 0 }
    $currentNetOut = if ($netAdapter) { $netAdapter.SentBytes } else { 0 }
    $currentTotal = $currentNetIn + $currentNetOut
    
    # Load previous network state
    try {
        $prev = Get-Content $PREV_NET_FILE | ConvertFrom-Json
    } catch {
        $prev = @{total=0;time=0}
    }
    
    $currentTime = [DateTimeOffset]::Now.ToUnixTimeSeconds()
    $timeDiff = $currentTime - $prev.time
    if ($timeDiff -lt 1) { $timeDiff = 2 }
    
    # Calculate network rate (KB/s)
    $totalRate = if ($prev.total -gt 0) { [math]::Max(0, ($currentTotal - $prev.total) / 1024 / $timeDiff) } else { 0 }
    
    # Attribute to running agents
    if ($agentsRunning -gt 0) {
        $perAgentRate = $totalRate / $agentsRunning
        $cursorNet = if ($cursorRunning -eq "true") { [math]::Round($perAgentRate, 1) } else { 0 }
        $copilotNet = if ($copilotRunning -eq "true") { [math]::Round($perAgentRate, 1) } else { 0 }
        $geminiNet = if ($geminiRunning -eq "true") { [math]::Round($perAgentRate, 1) } else { 0 }
        $codexNet = if ($codexRunning -eq "true") { [math]::Round($perAgentRate, 1) } else { 0 }
    } else {
        $cursorNet = $copilotNet = $geminiNet = $codexNet = 0
    }
    
    # Save network state
    @{total=$currentTotal;time=$currentTime;cursor_net=$cursorNet;copilot_net=$copilotNet;gemini_net=$geminiNet;codex_net=$codexNet} | ConvertTo-Json | Out-File $PREV_NET_FILE -Encoding UTF8
    
    # Update CPU history
    try {
        $history = Get-Content $HISTORY_FILE | ConvertFrom-Json
    } catch {
        $history = @{labels=@();cursor=@();copilot=@();gemini=@();codex=@()}
    }
    $history.labels += $timeLabel
    $history.cursor += $cursorCpu
    $history.copilot += $copilotCpu
    $history.gemini += $geminiCpu
    $history.codex += $codexCpu
    # Keep last 60
    if ($history.labels.Count -gt 60) {
        $history.labels = $history.labels[-60..-1]
        $history.cursor = $history.cursor[-60..-1]
        $history.copilot = $history.copilot[-60..-1]
        $history.gemini = $history.gemini[-60..-1]
        $history.codex = $history.codex[-60..-1]
    }
    $history | ConvertTo-Json -Depth 3 | Out-File $HISTORY_FILE -Encoding UTF8
    
    # Update network history
    try {
        $netHistory = Get-Content $NET_HISTORY_FILE | ConvertFrom-Json
    } catch {
        $netHistory = @{labels=@();cursor=@();copilot=@();gemini=@();codex=@()}
    }
    $netHistory.labels += $timeLabel
    $netHistory.cursor += $cursorNet
    $netHistory.copilot += $copilotNet
    $netHistory.gemini += $geminiNet
    $netHistory.codex += $codexNet
    if ($netHistory.labels.Count -gt 60) {
        $netHistory.labels = $netHistory.labels[-60..-1]
        $netHistory.cursor = $netHistory.cursor[-60..-1]
        $netHistory.copilot = $netHistory.copilot[-60..-1]
        $netHistory.gemini = $netHistory.gemini[-60..-1]
        $netHistory.codex = $netHistory.codex[-60..-1]
    }
    $netHistory | ConvertTo-Json -Depth 3 | Out-File $NET_HISTORY_FILE -Encoding UTF8
    
    # CSS classes
    $cursorClass = if ($cursorRunning -eq "true") { "running" } else { "" }
    $copilotClass = if ($copilotRunning -eq "true") { "running" } else { "" }
    $geminiClass = if ($geminiRunning -eq "true") { "running" } else { "" }
    $codexClass = if ($codexRunning -eq "true") { "running" } else { "" }
    
    $historyJson = $history | ConvertTo-Json -Depth 3 -Compress
    $netHistoryJson = $netHistory | ConvertTo-Json -Depth 3 -Compress

    # Write HTML
    $html = @"
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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #e0e0e0; padding: 20px; }
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
            <div class="last-update">Last update: $timeLabel • OS: Windows (auto-refreshes every 2s)</div>
        </header>
        <div class="status-grid">
            <div class="status-card">
                <div class="status-header"><div class="status-dot $cursorClass"></div><div class="status-name">Cursor</div></div>
                <div class="metrics">
                    <div class="metric"><div class="metric-value cpu">$cursorCpu%</div><div class="metric-label">CPU Usage</div></div>
                    <div class="metric"><div class="metric-value net">$cursorNet KB/s</div><div class="metric-label">Network</div></div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header"><div class="status-dot $copilotClass"></div><div class="status-name">Copilot</div></div>
                <div class="metrics">
                    <div class="metric"><div class="metric-value cpu">$copilotCpu%</div><div class="metric-label">CPU Usage</div></div>
                    <div class="metric"><div class="metric-value net">$copilotNet KB/s</div><div class="metric-label">Network</div></div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header"><div class="status-dot $geminiClass"></div><div class="status-name">Gemini</div></div>
                <div class="metrics">
                    <div class="metric"><div class="metric-value cpu">$geminiCpu%</div><div class="metric-label">CPU Usage</div></div>
                    <div class="metric"><div class="metric-value net">$geminiNet KB/s</div><div class="metric-label">Network</div></div>
                </div>
            </div>
            <div class="status-card">
                <div class="status-header"><div class="status-dot $codexClass"></div><div class="status-name">Codex</div></div>
                <div class="metrics">
                    <div class="metric"><div class="metric-value cpu">$codexCpu%</div><div class="metric-label">CPU Usage</div></div>
                    <div class="metric"><div class="metric-value net">$codexNet KB/s</div><div class="metric-label">Network</div></div>
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
        <div class="note">Network is attributed to active agents only</div>
    </div>
    <script>
        const historyData = $historyJson;
        const netHistoryData = $netHistoryJson;
        new Chart(document.getElementById('cpuChart').getContext('2d'), {
            type: 'line',
            data: { labels: historyData.labels, datasets: [
                { label: 'Cursor', data: historyData.cursor, borderColor: '#2196f3', tension: 0.4, borderWidth: 2 },
                { label: 'Copilot', data: historyData.copilot, borderColor: '#4caf50', tension: 0.4, borderWidth: 2 },
                { label: 'Gemini', data: historyData.gemini, borderColor: '#ff9800', tension: 0.4, borderWidth: 2 },
                { label: 'Codex', data: historyData.codex, borderColor: '#9c27b0', tension: 0.4, borderWidth: 2 }
            ]},
            options: { responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: { x: { ticks: { color: '#888', maxRotation: 0, maxTicksLimit: 8 }, grid: { color: '#333' } },
                    y: { beginAtZero: true, max: 100, ticks: { color: '#888', callback: v => v + '%' }, grid: { color: '#333' } } } }
        });
        new Chart(document.getElementById('netChart').getContext('2d'), {
            type: 'line',
            data: { labels: netHistoryData.labels, datasets: [
                { label: 'Cursor', data: netHistoryData.cursor, borderColor: '#2196f3', backgroundColor: 'rgba(33,150,243,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                { label: 'Copilot', data: netHistoryData.copilot, borderColor: '#4caf50', backgroundColor: 'rgba(76,175,80,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                { label: 'Gemini', data: netHistoryData.gemini, borderColor: '#ff9800', backgroundColor: 'rgba(255,152,0,0.1)', tension: 0.4, borderWidth: 2, fill: true },
                { label: 'Codex', data: netHistoryData.codex, borderColor: '#9c27b0', backgroundColor: 'rgba(156,39,176,0.1)', tension: 0.4, borderWidth: 2, fill: true }
            ]},
            options: { responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: { x: { ticks: { color: '#888', maxRotation: 0, maxTicksLimit: 8 }, grid: { color: '#333' } },
                    y: { beginAtZero: true, ticks: { color: '#888', callback: v => v + ' KB/s' }, grid: { color: '#333' } } } }
        });
    </script>
</body>
</html>
"@
    
    $html | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8
    
    Start-Sleep -Seconds 2
}
