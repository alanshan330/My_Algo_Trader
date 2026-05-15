document.addEventListener('DOMContentLoaded', () => {
    
    // Initialize Premium Calendar
    flatpickr("#start_date", { theme: "dark", dateFormat: "Y-m-d" });
    flatpickr("#end_date", { theme: "dark", dateFormat: "Y-m-d" });
    
    // Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    function switchTab(targetId) {
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        document.querySelector(`.tab-btn[data-target="${targetId}"]`).classList.add('active');
        document.getElementById(targetId).classList.add('active');
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.target));
    });

    // Native File Browser
    const browseBtn = document.getElementById('browse-btn');
    const csvInput = document.getElementById('csv_path');
    
    browseBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/browse_csv');
            const data = await res.json();
            if (data.status === 'success' && data.path) {
                csvInput.value = data.path;
            }
        } catch (e) {
            console.error("Browse failed", e);
        }
    });

    // Data Table Rendering
    const tableHead = document.getElementById('table-head');
    const tableBody = document.getElementById('table-body');

    function renderTable(dataArray) {
        tableHead.innerHTML = '';
        tableBody.innerHTML = '';
        if (!dataArray || dataArray.length === 0) return;

        // Create Headers
        const headers = Object.keys(dataArray[0]);
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            tableHead.appendChild(th);
        });

        // Create Rows
        dataArray.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                // Format numbers slightly if possible
                let val = row[header];
                if (typeof val === 'number') {
                    // Check if it's an integer or float
                    val = Number.isInteger(val) ? val : parseFloat(val).toFixed(2);
                }
                td.textContent = val !== null ? val : '';
                tr.appendChild(td);
            });
            tableBody.appendChild(tr);
        });

        // Add Total Row if it's a backtest ledger (has P/L USD)
        if (headers.includes("P/L USD")) {
            const tfoot = document.createElement('tr');
            tfoot.style.fontWeight = 'bold';
            tfoot.style.background = 'rgba(255, 255, 255, 0.05)';
            tfoot.style.borderTop = '2px solid rgba(255,255,255,0.2)';
            
            headers.forEach(header => {
                const td = document.createElement('td');
                if (header === "Date") {
                    td.textContent = "TOTAL";
                } else if (header === "P/L Pts" || header === "P/L USD" || header === "Profit %") {
                    const sum = dataArray.reduce((acc, row) => {
                        const val = parseFloat(row[header]) || 0;
                        return acc + val;
                    }, 0);
                    td.textContent = sum.toFixed(2);
                } else {
                    td.textContent = "-";
                }
                tfoot.appendChild(td);
            });
            tableBody.appendChild(tfoot);
        }
    }

    let currentData = null;
    const exportBtn = document.getElementById('export-btn');

    exportBtn.addEventListener('click', () => {
        if (!currentData || currentData.length === 0) return;
        
        const headers = Object.keys(currentData[0]);
        const csvRows = [];
        
        // Headers
        csvRows.push(headers.join(','));
        
        // Data
        currentData.forEach(row => {
            const values = headers.map(header => {
                const escape = ('' + (row[header] || '')).replace(/"/g, '""');
                return `"${escape}"`;
            });
            csvRows.push(values.join(','));
        });
        
        const csvString = csvRows.join('\n');
        const blob = new Blob([csvString], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `antigravity_export_${new Date().getTime()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    });
    
    // Toggle Mode
    const modeBtns = document.querySelectorAll('.toggle-btn');
    const modeInput = document.getElementById('mode');
    
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            modeInput.value = btn.dataset.value;
            
            // Autosave on toggle
            fetch('/api/save_state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getParams())
            });
        });
    });

    // Make sure initial mode is reflected visually
    const currentMode = modeInput.value;
    modeBtns.forEach(b => b.classList.remove('active'));
    document.querySelector(`.toggle-btn[data-value="${currentMode}"]`)?.classList.add('active');

    // Strategy Tabs
    const stratTabs = document.querySelectorAll('.strat-tab');
    const ibsPanel = document.getElementById('ibs-strat-panel');
    const newPanel = document.getElementById('new-strat-panel');
    const dbPanel = document.getElementById('db-strat-panel');
    
    stratTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            stratTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            if (tab.dataset.target === 'new-strat') {
                ibsPanel.style.display = 'none';
                dbPanel.style.display = 'none';
                newPanel.style.display = 'block';
                logToTerminal("Switched to Day Trading workspace.", "system");
            } else if (tab.dataset.target === 'db-strat') {
                ibsPanel.style.display = 'none';
                newPanel.style.display = 'none';
                dbPanel.style.display = 'block';
                logToTerminal("Switched to Database Analytics workspace.", "system");
            } else {
                newPanel.style.display = 'none';
                dbPanel.style.display = 'none';
                ibsPanel.style.display = 'block';
                logToTerminal("Switched to IBS Mean Reversion workspace.", "system");
            }
        });
    });

    // Terminal Logging
    const terminal = document.getElementById('terminal');
    function logToTerminal(msg, type = 'normal') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.textContent = msg;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }

    // Launch Engine
    const launchBtn = document.getElementById('launch-btn');
    const btnText = launchBtn.querySelector('.btn-text');
    const spinner = document.getElementById('spinner');

    function getParams() {
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

    // Auto-save State on any input change
    const allInputs = document.querySelectorAll('input, select');
    allInputs.forEach(input => {
        input.addEventListener('change', () => {
            fetch('/api/save_state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getParams())
            });
        });
    });



    const stopBtn = document.getElementById('stop-btn');
    const loadDbBtn = document.getElementById('load-db-btn');
    const loadChartBtn = document.getElementById('load-chart-btn');
    
    // Initialize TradingView Lightweight Chart
    let tvChart = null;
    let ema9Series = null;
    let ema21Series = null;
    let stochKSeries = null;
    let stochDSeries = null;
    
    function initChart() {
        if (tvChart) return;
        const container = document.getElementById('tvchart');
        tvChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 500,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#d1d5db',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
            },
            timeScale: { timeVisible: true, secondsVisible: false },
        });
        candlestickSeries = tvChart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
            wickUpColor: '#10b981', wickDownColor: '#ef4444'
        });
        
        ema9Series = tvChart.addLineSeries({ color: '#3b82f6', lineWidth: 1, title: 'EMA 9' });
        ema21Series = tvChart.addLineSeries({ color: '#f59e0b', lineWidth: 1, title: 'EMA 21' });
        
        stochKSeries = tvChart.addLineSeries({ color: '#8b5cf6', lineWidth: 1, priceScaleId: 'stoch', title: '%K' });
        stochDSeries = tvChart.addLineSeries({ color: '#ec4899', lineWidth: 1, priceScaleId: 'stoch', title: '%D' });
        
        tvChart.priceScale('stoch').applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });
        candlestickSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.1, bottom: 0.25 },
        });
        
        const legend = document.getElementById('chart-legend');
        tvChart.subscribeCrosshairMove((param) => {
            if (param.point === undefined || !param.time || param.point.x < 0 || param.point.x > container.clientWidth || param.point.y < 0 || param.point.y > container.clientHeight) {
                // Not over chart
                legend.innerHTML = '';
                return;
            }
            
            const data = param.seriesPrices.get(candlestickSeries);
            if (!data) return;
            
            // In v3.8.0 seriesPrices.get returns the raw price data object or the close price
            // Wait, for Candlestick, it returns an OHLC object.
            const o = data.open !== undefined ? data.open : data;
            const h = data.high !== undefined ? data.high : data;
            const l = data.low !== undefined ? data.low : data;
            const c = data.close !== undefined ? data.close : data;
            
            const ticker = document.getElementById('dt-ticker').value;
            const color = c >= o ? '#10b981' : '#ef4444';
            
            const change = (c - o);
            const changePercent = (change / o * 100).toFixed(2);
            const sign = change >= 0 ? '+' : '';
            
            legend.innerHTML = `
                <div style="font-weight: 600; color: white;">${ticker}</div>
                <div>O <span style="color: ${color}">${o.toFixed(2)}</span></div>
                <div>H <span style="color: ${color}">${h.toFixed(2)}</span></div>
                <div>L <span style="color: ${color}">${l.toFixed(2)}</span></div>
                <div>C <span style="color: ${color}">${c.toFixed(2)}</span></div>
                <div><span style="color: ${color}">${sign}${change.toFixed(2)} (${sign}${changePercent}%)</span></div>
            `;
        });
        
        window.addEventListener('resize', () => {
            tvChart.applyOptions({ width: container.clientWidth });
        });
    }

    let liveChartInterval = null;
    let lastChartBar = null;

    loadChartBtn?.addEventListener('click', async () => {
        logToTerminal("Initializing chart...", "system");
        try {
            initChart();
        } catch (e) {
            logToTerminal(`Chart Init Error: ${e.message}`, "error");
            return;
        }
        
        const btn = loadChartBtn;
        btn.textContent = "Loading...";
        btn.disabled = true;
        
        try {
            const ticker = document.getElementById('dt-ticker').value;
            const res = await fetch('/api/chart_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: ticker,
                    timeframe: document.getElementById('dt-timeframe').value
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                const chartData = data.data || [];
                candlestickSeries.setData(chartData);
                
                // Indicators mapping
                const ema9Data = chartData.map(d => ({ time: d.time, value: d.ema9 || 0 }));
                const ema21Data = chartData.map(d => ({ time: d.time, value: d.ema21 || 0 }));
                const stochKData = chartData.map(d => ({ time: d.time, value: d.stoch_k || 0 }));
                const stochDData = chartData.map(d => ({ time: d.time, value: d.stoch_d || 0 }));
                
                ema9Series.setData(ema9Data);
                ema21Series.setData(ema21Data);
                stochKSeries.setData(stochKData);
                stochDSeries.setData(stochDData);
                
                // TD Sequential markers
                const markers = [];
                chartData.forEach(d => {
                    if (d.td_setup === 9) {
                        markers.push({
                            time: d.time,
                            position: d.td_dir === -1 ? 'aboveBar' : 'belowBar',
                            color: d.td_dir === -1 ? '#ef4444' : '#10b981',
                            shape: d.td_dir === -1 ? 'arrowDown' : 'arrowUp',
                            text: '9'
                        });
                    }
                });
                candlestickSeries.setMarkers(markers);
                
                logToTerminal(`Loaded ${chartData.length} candles for ${ticker}`, 'success');
                
                if (chartData.length > 0) {
                    lastChartBar = chartData[chartData.length - 1];
                }
                
                // Start live price polling
                if (liveChartInterval) clearInterval(liveChartInterval);
                liveChartInterval = setInterval(async () => {
                    if (!lastChartBar) return;
                    try {
                        const priceRes = await fetch(`/api/live_price?ticker=${ticker}`);
                        const priceData = await priceRes.json();
                        if (priceData.status === 'success' && priceData.data.price > 0) {
                            const p = priceData.data.price;
                            const t = priceData.data.time;
                            
                            // If the time has moved into a new timeframe, we should ideally fetch a new bar
                            // For simplicity, we just update the current bar's close, high, low
                            const updatedBar = {
                                time: lastChartBar.time,
                                open: lastChartBar.open,
                                high: Math.max(lastChartBar.high, p),
                                low: Math.min(lastChartBar.low, p),
                                close: p
                            };
                            candlestickSeries.update(updatedBar);
                            lastChartBar = updatedBar;
                        }
                    } catch (e) {}
                }, 1000); // Poll every 1 second
                
            } else {
                logToTerminal(`Chart Error: ${data.message}`, 'error');
            }
        } catch (err) {
            logToTerminal(`Chart Network Error: ${err.message}`, 'error');
        } finally {
            btn.textContent = "Load Data";
            btn.disabled = false;
        }
    });

    loadDbBtn.addEventListener('click', async () => {
        logToTerminal('Querying SQLite Database...', 'system');
        try {
            const res = await fetch('/api/db/trades');
            const data = await res.json();
            if (data.status === 'success') {
                logToTerminal(`SUCCESS: Loaded ${data.data.length} trades from database.`, 'success');
                if (data.data.length > 0) {
                    currentData = data.data;
                    renderTable(data.data);
                    switchTab('data-table');
                } else {
                    logToTerminal('No trades found in the database yet.', 'system');
                }
            } else {
                logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    const loadDbBacktestsBtn = document.getElementById('load-db-backtests-btn');
    loadDbBacktestsBtn?.addEventListener('click', async () => {
        logToTerminal('Querying SQLite for Backtest Results...', 'system');
        try {
            const res = await fetch('/api/db/backtests');
            const data = await res.json();
            if (data.status === 'success') {
                logToTerminal(`SUCCESS: Loaded ${data.data.length} backtest summaries from database.`, 'success');
                if (data.data.length > 0) {
                    currentData = data.data;
                    renderTable(data.data);
                    switchTab('data-table');
                } else {
                    logToTerminal('No backtests found in the database yet.', 'system');
                }
            } else {
                logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    launchBtn.addEventListener('click', async () => {
        if(launchBtn.classList.contains('loading')) return;

        // Gather params
        const params = getParams();

        // UI Loading State
        launchBtn.classList.add('loading');
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');

        logToTerminal(`\n> Initializing Engine in ${params.mode.toUpperCase()} mode...`, 'system');

        try {
            if (params.mode === 'backtest') {
                logToTerminal('Running Pandas Backtest (this may take a few seconds)...');
                const res = await fetch('/api/backtest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    logToTerminal(data.report, 'success');
                    logToTerminal(`Ledger loaded into Data Results tab.`, 'system');
                    
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
                        kpiContainer.classList.remove('hidden');
                    } else {
                        kpiContainer.classList.add('hidden');
                    }
                    
                    if (data.data) {
                        currentData = data.data;
                        renderTable(data.data);
                        switchTab('data-table');
                        exportBtn.classList.remove('hidden');
                    }
                } else {
                    logToTerminal(`Error: ${data.message}`, 'error');
                }
            } 
            else if (params.mode === 'optimize') {
                logToTerminal('Running Parameter Sweep Optimizer over 600+ combinations...');
                switchTab('terminal'); // make sure we watch terminal during long run
                const res = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    logToTerminal(data.output, 'success');
                    if (data.data) {
                        currentData = data.data;
                        renderTable(data.data);
                        switchTab('data-table');
                        exportBtn.classList.remove('hidden');
                    }
                } else {
                    logToTerminal(`Error: ${data.message}`, 'error');
                }
            }
            else if (params.mode === 'live') {
                logToTerminal('Launching Live Trader in Background...', 'system');
                const res = await fetch('/api/live', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    logToTerminal('SUCCESS: Live Trader is now running silently in the background.', 'success');
                    stopBtn.classList.remove('hidden');
                    launchBtn.classList.add('hidden');
                } else {
                    logToTerminal(`Error: ${data.message}`, 'error');
                }
            }
        } catch (err) {
            logToTerminal(`Network Error: ${err.message}`, 'error');
        } finally {
            launchBtn.classList.remove('loading');
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    });

    stopBtn.addEventListener('click', async () => {
        logToTerminal('Stopping Live Trader...', 'system');
        const res = await fetch('/api/stop_live', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            logToTerminal('SUCCESS: Live Trader Stopped.', 'success');
            stopBtn.classList.add('hidden');
            launchBtn.classList.remove('hidden');
        } else {
            logToTerminal(`Error: ${data.message}`, 'error');
        }
    });

    // Periodically fetch live results and logs if in live mode
    let lastLog = "";
    setInterval(async () => {
        if (modeInput.value === 'live') {
            try {
                // Fetch Trades
                const resTrades = await fetch('/api/live_results');
                const dataTrades = await resTrades.json();
                if (dataTrades.status === 'success' && dataTrades.data && dataTrades.data.length > 0) {
                    currentData = dataTrades.data;
                    renderTable(dataTrades.data);
                }

                // Fetch Logs
                const resLogs = await fetch('/api/live_logs');
                const dataLogs = await resLogs.json();
                if (dataLogs.status === 'success' && dataLogs.logs !== lastLog) {
                    // Update terminal with new logs
                    const newLogs = dataLogs.logs.replace(lastLog, "");
                    if (newLogs.trim()) {
                        newLogs.split("\n").forEach(line => {
                            if (line.trim()) logToTerminal(line, 'live');
                        });
                        lastLog = dataLogs.logs;
                    }
                }
            } catch (err) {
                console.error("Failed to fetch live updates:", err);
            }
        }
    }, 5000);
});
