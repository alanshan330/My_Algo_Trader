/**
 * Antigravity Web Dashboard - Day Trading Strategy Module
 * Handles TradingView lightweight charting, real-time prices updates,
 * indicators calculation displaying, file pickers, backtesting, and last results loading.
 */

document.addEventListener('DOMContentLoaded', () => {
    const loadChartBtn = document.getElementById('load-chart-btn');
    const dtBacktestBtn = document.getElementById('dt-backtest-btn');
    const dtLiveBtn = document.getElementById('dt-live-btn');
    const dtTickerInput = document.getElementById('dt-ticker');
    const futuresBanner = document.getElementById('futures-csv-banner');
    const reloadBtn = document.getElementById('dt-reload-result-btn');

    if (!loadChartBtn) return; // Day Trading panel not present in DOM

    // --- TradingView Chart Engine ---
    let tvChart = null;
    let candlestickSeries = null;
    let ema9Series = null;
    let ema21Series = null;
    let stochKSeries = null;
    let stochDSeries = null;
    let livePriceInterval = null;
    let lastChartBar = null;

    function initChart() {
        if (tvChart) return;
        const container = document.getElementById('tvchart');
        if (!container) return;

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
            if (!legend) return;
            if (param.point === undefined || !param.time || param.point.x < 0 || param.point.x > container.clientWidth || param.point.y < 0 || param.point.y > container.clientHeight) {
                legend.innerHTML = '';
                return;
            }
            
            const data = param.seriesPrices.get(candlestickSeries);
            if (!data) return;
            
            const o = data.open !== undefined ? data.open : data;
            const h = data.high !== undefined ? data.high : data;
            const l = data.low !== undefined ? data.low : data;
            const c = data.close !== undefined ? data.close : data;
            
            const ticker = dtTickerInput?.value || 'NQ';
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

    // --- Autosave on Parameter Changes ---
    const dtInputs = document.querySelectorAll('#new-strat-panel input, #new-strat-panel select');
    function saveDTState() {
        fetch('/api/save_state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(getDTParams('backtest'))
        }).catch(err => console.error("Error auto-saving DT state:", err));
    }
    dtInputs.forEach(input => {
        input.addEventListener('change', saveDTState);
    });

    // --- Load Chart Data ---
    loadChartBtn?.addEventListener('click', async () => {
        window.logToTerminal("Initializing chart...", "system");
        try {
            initChart();
        } catch (e) {
            window.logToTerminal(`Chart Init Error: ${e.message}`, "error");
            return;
        }

        const btn = loadChartBtn;
        btn.textContent = "Loading...";
        btn.disabled = true;

        try {
            const ticker = dtTickerInput.value;
            const csvPath = document.getElementById('dt-csv-path')?.value || '';
            const res = await fetch('/api/chart_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: ticker,
                    timeframe: document.getElementById('dt-timeframe').value,
                    csv_path: csvPath
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                const chartData = data.data || [];
                candlestickSeries.setData(chartData);
                window.currentChartData = chartData;
                
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
                
                window.logToTerminal(`Loaded ${chartData.length} candles for ${ticker}`, 'success');
                
                if (chartData.length > 0) {
                    lastChartBar = chartData[chartData.length - 1];
                }
                
                // Start live price updates loop
                if (livePriceInterval) clearInterval(livePriceInterval);
                livePriceInterval = setInterval(async () => {
                    if (!lastChartBar) return;
                    try {
                        const priceRes = await fetch(`/api/live_price?ticker=${ticker}`);
                        const priceData = await priceRes.json();
                        if (priceData.status === 'success' && priceData.data.price > 0) {
                            const p = priceData.data.price;
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
                }, 1000);
                
            } else {
                window.logToTerminal(`Chart Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Chart Network Error: ${err.message}`, 'error');
        } finally {
            btn.textContent = "Load Data";
            btn.disabled = false;
        }
    });

    // --- Futures warning banner trigger ---
    const FUTURES_TICKERS = new Set(['NQ','ES','YM','RTY','CL','GC','MNQ','MES','MYM','M2K','ZB','ZN']);
    function updateFuturesBanner() {
        const t = (dtTickerInput?.value || '').toUpperCase().trim();
        if (futuresBanner) futuresBanner.style.display = FUTURES_TICKERS.has(t) ? 'block' : 'none';
    }
    dtTickerInput?.addEventListener('input', updateFuturesBanner);
    updateFuturesBanner();

    // --- Native File Picker ---
    document.getElementById('dt-browse-btn')?.addEventListener('click', async () => {
        try {
            window.logToTerminal('Opening Day Trading file browser...', 'system');
            const res = await fetch('/api/browse_csv');
            const data = await res.json();
            if (data.status === 'success' && data.path) {
                document.getElementById('dt-csv-path').value = data.path;
                document.getElementById('dt-csv-path').style.color = '';
                window.logToTerminal(`Day Trading CSV selected: ${data.path}`, 'success');
                saveDTState();
            } else {
                window.logToTerminal('No file selected.', 'system');
            }
        } catch (err) {
            window.logToTerminal(`Browse error: ${err.message}`, 'error');
        }
    });

    // --- Clear CSV File ---
    document.getElementById('dt-clear-csv-btn')?.addEventListener('click', () => {
        const csvInput = document.getElementById('dt-csv-path');
        if (csvInput) {
            csvInput.value = '';
            csvInput.style.color = '';
        }
        window.logToTerminal('CSV file cleared. Day Trading Load Data will fetch online feeds.', 'system');
        saveDTState();
    });

    // --- Params builder ---
    function getDTParams(mode) {
        const today = new Date().toISOString().slice(0, 10);
        const oneYearAgo = new Date(Date.now() - 365*24*60*60*1000).toISOString().slice(0, 10);
        const dtStart = document.getElementById('dt-start-date')?.value || oneYearAgo;
        const dtEnd   = document.getElementById('dt-end-date')?.value   || today;
        return {
            mode: mode,
            symbol: dtTickerInput.value,
            timeframe: document.getElementById('dt-timeframe').value,
            sleep_time: document.getElementById('dt-timeframe').value,
            strategy: document.getElementById('dt-strategy').value,
            start_date: dtStart,
            end_date: dtEnd,
            csv_path: document.getElementById('dt-csv-path')?.value || '',
            entry_threshold: 0.0,
            exit_threshold: 0.0,
            max_hold_days: 0,
            max_contracts: 0,
            trend_filter: false
        };
    }

    // --- Run Backtest ---
    dtBacktestBtn?.addEventListener('click', async () => {
        window.logToTerminal(`\n> Initializing Day Trading Backtest Engine...`, 'system');
        const params = getDTParams('backtest');
        if (window.currentChartData && window.currentChartData.length > 0) {
            params.chart_data = window.currentChartData;
        }

        try {
            const res = await fetch('/api/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const data = await res.json();
            if (data.status === 'success') {
                window.logToTerminal(data.report, 'success');
                window.lastBacktestReport = data.report;
                window.lastBacktestSource = 'dt';
                
                // Parse KPIs from report text
                const kpiContainer = document.getElementById('kpi-container');
                if (data.report) {
                    const trMatch = data.report.match(/Total Trades:\s*(\d+)/);
                    const wrMatch = data.report.match(/Win Rate:\s*([\d\.]+%)/);
                    const ddMatch = data.report.match(/Max Drawdown:\s*(-\$[\d\.]+)/);
                    const pnlMatch = data.report.match(/Total Dollar Return[^:]*:\s*(\$[\+\-\d\.]+)/);
                    
                    if (trMatch && document.getElementById('kpi-trades')) document.getElementById('kpi-trades').textContent = trMatch[1];
                    if (wrMatch && document.getElementById('kpi-winrate')) document.getElementById('kpi-winrate').textContent = wrMatch[1];
                    if (ddMatch && document.getElementById('kpi-drawdown')) document.getElementById('kpi-drawdown').textContent = ddMatch[1];
                    if (pnlMatch && document.getElementById('kpi-profit')) document.getElementById('kpi-profit').textContent = pnlMatch[1];
                    kpiContainer?.classList.remove('hidden');
                }
                
                if (data.data) {
                    window.currentTableData = data.data;
                    window.renderTable(data.data);
                    window.switchTab('data-table');
                    if (reloadBtn) reloadBtn.classList.remove('hidden');
                }
            } else {
                window.logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    // --- Reload Last Backtest Result ---
    reloadBtn?.addEventListener('click', async () => {
        if (window.currentTableData.length > 0 && window.lastBacktestSource === 'dt') {
            window.renderTable(window.currentTableData);
            window.switchTab('data-table');
            if (window.lastBacktestReport) window.logToTerminal(window.lastBacktestReport, 'success');
            window.logToTerminal('Last backtest result restored.', 'system');
            return;
        }
        try {
            window.logToTerminal('Fetching last backtest from disk...', 'system');
            const res = await fetch('/api/last_backtest');
            const data = await res.json();
            if (data.status === 'success' && data.data && data.data.length > 0) {
                window.currentTableData = data.data;
                window.lastBacktestSource = 'dt';
                window.renderTable(data.data);
                window.switchTab('data-table');
                window.logToTerminal(`Loaded ${data.data.length} rows from: ${data.file}`, 'success');
            } else {
                window.logToTerminal('No previous backtest found on disk.', 'system');
            }
        } catch (err) {
            window.logToTerminal(`Error loading last result: ${err.message}`, 'error');
        }
    });

    // --- Launch Live Day Trader ---
    dtLiveBtn?.addEventListener('click', async () => {
        window.logToTerminal(`\n> Initializing Live Day Trader (Background)...`, 'system');
        const params = getDTParams('live');
        try {
            const res = await fetch('/api/live', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const data = await res.json();
            if (data.status === 'success') {
                window.logToTerminal(data.message, 'success');
            } else {
                window.logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    window.logToTerminal("Day Trading Strategy Module Initialized.", "system");
});
