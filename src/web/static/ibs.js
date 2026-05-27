/**
 * Antigravity Web Dashboard - IBS Mean Reversion Strategy Module
 * Handles parameter gathering, auto-saving, backtest/optimize/live launching,
 * and live-updating results specifically for the IBS Mean Reversion workspace.
 */

document.addEventListener('DOMContentLoaded', () => {
    const launchBtn = document.getElementById('launch-btn');
    const stopBtn = document.getElementById('stop-btn');
    const modeInput = document.getElementById('mode');
    const modeBtns = document.querySelectorAll('#mode-toggle .toggle-btn');
    const btnText = launchBtn?.querySelector('.btn-text');
    const spinner = document.getElementById('spinner');

    if (!launchBtn) return; // IBS panel not present in DOM

    // --- Parameter Ingestion ---
    function getIBSParams() {
        return {
            mode: modeInput.value,
            ticker: document.getElementById('ticker').value,
            timeframe: document.getElementById('timeframe').value,
            strategy: document.getElementById('strategy').value,
            start_date: document.getElementById('start_date').value,
            end_date: document.getElementById('end_date').value,
            csv_path: document.getElementById('csv_path').value,
            entry_ibs: parseFloat(document.getElementById('entry_ibs').value) || 0.21,
            exit_ibs: parseFloat(document.getElementById('exit_ibs').value) || 0.87,
            max_hold_days: parseInt(document.getElementById('max_hold_days').value) || 0,
            max_contracts: parseInt(document.getElementById('max_contracts').value) || 0,
            trend_filter: document.getElementById('trend_filter').checked
        };
    }

    // --- Autosave on Parameter Changes ---
    const ibsInputs = document.querySelectorAll('#ibs-strat-panel input, #ibs-strat-panel select');
    function saveIBSState() {
        fetch('/api/save_state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(getIBSParams())
        }).catch(err => console.error("Error auto-saving state:", err));
    }
    ibsInputs.forEach(input => {
        input.addEventListener('change', saveIBSState);
    });

    // --- Mode Select Handler ---
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            modeInput.value = btn.dataset.value;
            saveIBSState();
        });
    });

    // Make sure initial mode is reflected visually on reload
    const currentMode = modeInput.value;
    modeBtns.forEach(b => b.classList.remove('active'));
    document.querySelector(`#mode-toggle .toggle-btn[data-value="${currentMode}"]`)?.classList.add('active');

    // --- IBS Native File Picker ---
    const browseBtn = document.getElementById('browse-btn');
    const csvInput = document.getElementById('csv_path');
    browseBtn?.addEventListener('click', async () => {
        try {
            window.logToTerminal('Opening IBS file browser...', 'system');
            const res = await fetch('/api/browse_csv');
            const data = await res.json();
            if (data.status === 'success' && data.path) {
                csvInput.value = data.path;
                window.logToTerminal(`IBS CSV selected: ${data.path}`, 'success');
                saveIBSState();
            } else {
                window.logToTerminal('No file selected.', 'system');
            }
        } catch (e) {
            window.logToTerminal(`Browse failed: ${e.message}`, 'error');
        }
    });

    // --- Launch Engine ---
    launchBtn.addEventListener('click', async () => {
        if (launchBtn.classList.contains('loading')) return;

        const params = getIBSParams();

        // UI Loading State
        launchBtn.classList.add('loading');
        if (btnText) btnText.classList.add('hidden');
        if (spinner) spinner.classList.remove('hidden');

        window.logToTerminal(`\n> Initializing IBS Mean Reversion in ${params.mode.toUpperCase()} mode...`, 'system');

        try {
            if (params.mode === 'backtest') {
                window.logToTerminal('Running Pandas Backtest (this may take a few seconds)...');
                const res = await fetch('/api/backtest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    window.logToTerminal(data.report, 'success');
                    window.logToTerminal(`Ledger loaded into Data Results tab.`, 'system');
                    window.lastBacktestSource = 'ibs';
                    
                    // Parse KPIs from report text
                    const kpiContainer = document.getElementById('kpi-container');
                    if (data.report) {
                        const trMatch = data.report.match(/Total Trades:\s*(\d+)/);
                        const wrMatch = data.report.match(/Win Rate:\s*([\d\.]+%)/);
                        const ddMatch = data.report.match(/Max Drawdown:\s*(-\$[\d\.]+)/);
                        const pnlMatch = data.report.match(/Total Dollar Return[^:]*:\s*(\$[\+\-\d\.]+)/);
                        
                        if (trMatch) document.getElementById('kpi-trades').textContent = trMatch[1];
                        if (wrMatch) document.getElementById('kpi-winrate').textContent = wrMatch[1];
                        if (ddMatch) document.getElementById('kpi-drawdown').textContent = ddMatch[1];
                        if (pnlMatch) document.getElementById('kpi-profit').textContent = pnlMatch[1];
                        kpiContainer?.classList.remove('hidden');
                    } else {
                        kpiContainer?.classList.add('hidden');
                    }
                    
                    if (data.data) {
                        window.currentTableData = data.data;
                        window.renderTable(data.data);
                        window.switchTab('data-table');
                    }
                } else {
                    window.logToTerminal(`Error: ${data.message}`, 'error');
                }
            } 
            else if (params.mode === 'optimize') {
                window.logToTerminal('Running Parameter Sweep Optimizer over 600+ combinations...');
                window.switchTab('terminal');
                const res = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    window.logToTerminal(data.output, 'success');
                    window.lastBacktestSource = 'ibs';
                    if (data.data) {
                        window.currentTableData = data.data;
                        window.renderTable(data.data);
                        window.switchTab('data-table');
                    }
                } else {
                    window.logToTerminal(`Error: ${data.message}`, 'error');
                }
            }
            else if (params.mode === 'live') {
                window.logToTerminal('Launching Live Trader in Background...', 'system');
                const res = await fetch('/api/live', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    window.logToTerminal('SUCCESS: Live Trader is now running silently in the background.', 'success');
                    stopBtn?.classList.remove('hidden');
                    launchBtn.classList.add('hidden');
                } else {
                    window.logToTerminal(`Error: ${data.message}`, 'error');
                }
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        } finally {
            launchBtn.classList.remove('loading');
            if (btnText) btnText.classList.remove('hidden');
            if (spinner) spinner.classList.add('hidden');
        }
    });

    // --- Stop Engine ---
    stopBtn?.addEventListener('click', async () => {
        window.logToTerminal('Stopping Live Trader...', 'system');
        const res = await fetch('/api/stop_live', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            window.logToTerminal('SUCCESS: Live Trader Stopped.', 'success');
            stopBtn.classList.add('hidden');
            launchBtn.classList.remove('hidden');
        } else {
            window.logToTerminal(`Error: ${data.message}`, 'error');
        }
    });

    // --- Live Trading Output Polling ---
    let lastLog = "";
    setInterval(async () => {
        if (modeInput.value === 'live') {
            try {
                // Fetch Trades
                const resTrades = await fetch('/api/live_results');
                const dataTrades = await resTrades.json();
                if (dataTrades.status === 'success' && dataTrades.data && dataTrades.data.length > 0) {
                    if (window.lastBacktestSource !== 'dt') {
                        window.currentTableData = dataTrades.data;
                        if (document.getElementById('data-table').classList.contains('active')) {
                            window.renderTable(dataTrades.data);
                        }
                    }
                }

                // Fetch Logs
                const resLogs = await fetch('/api/live_logs');
                const dataLogs = await resLogs.json();
                if (dataLogs.status === 'success' && dataLogs.logs !== lastLog) {
                    const newLogs = dataLogs.logs.replace(lastLog, "");
                    if (newLogs.trim()) {
                        newLogs.split("\n").forEach(line => {
                            if (line.trim()) window.logToTerminal(line, 'live');
                        });
                        lastLog = dataLogs.logs;
                    }
                }
            } catch (err) {
                console.error("Failed to fetch IBS live updates:", err);
            }
        }
    }, 5000);

    window.logToTerminal("IBS Mean Reversion Strategy Module Initialized.", "system");
});
