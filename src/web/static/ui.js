/**
 * Antigravity Web Dashboard - Shared UI & Core Utilities
 * Handles workspace tabs, output console log, results table, and shared state.
 */

// Global Shared State
window.currentTableData = [];
window.currentChartData = [];
window.lastBacktestReport = '';
window.lastBacktestSource = '';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Calendars
    flatpickr("#start_date", { theme: "dark", dateFormat: "Y-m-d" });
    flatpickr("#end_date", { theme: "dark", dateFormat: "Y-m-d" });
    flatpickr("#dt-start-date", { theme: "dark", dateFormat: "Y-m-d" });
    flatpickr("#dt-end-date", { theme: "dark", dateFormat: "Y-m-d" });

    // --- Tab Switching: Console Log vs Data Results ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    window.switchTab = function(targetId) {
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        const targetBtn = document.querySelector(`.tab-btn[data-target="${targetId}"]`);
        const targetContent = document.getElementById(targetId);
        
        if (targetBtn) targetBtn.classList.add('active');
        if (targetContent) targetContent.classList.add('active');
    };

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => window.switchTab(btn.dataset.target));
    });

    // --- Terminal Console Log ---
    const terminal = document.getElementById('terminal');
    window.logToTerminal = function(msg, type = 'normal') {
        if (!terminal) return;
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.textContent = msg;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    };

    // --- Data Results Table ---
    const tableHead = document.getElementById('table-head');
    const tableBody = document.getElementById('table-body');
    const exportBtn = document.getElementById('export-btn');

    window.renderTable = function(dataArray) {
        if (!tableHead || !tableBody) return;
        tableHead.innerHTML = '';
        tableBody.innerHTML = '';
        if (!dataArray || dataArray.length === 0) {
            if (exportBtn) exportBtn.classList.add('hidden');
            return;
        }

        if (exportBtn) exportBtn.classList.remove('hidden');

        // Create Headers
        const rawHeaders = Object.keys(dataArray[0]);
        const hiddenCols = ['ledger_json', 'id', 'avg_loss', 'avg_win', 'expectancy', 'max_consec_loss', 'profit_factor', 'sharpe_ratio', 'total_profit', 'best_profit', 'P/L USD', 'Dollars'];
        
        const desiredOrder = ['strategy', 'ticker', 'timeframe', 'entry_ibs', 'exit_ibs', 'total_trades', 'win_rate', 'avg_trade_pl', 'max_drawdown', 'timestamp'];
        const headers = rawHeaders.filter(h => !hiddenCols.includes(h)).sort((a, b) => {
            const indexA = desiredOrder.indexOf(a);
            const indexB = desiredOrder.indexOf(b);
            if (indexA === -1 && indexB === -1) return 0;
            if (indexA === -1) return 1;
            if (indexB === -1) return -1;
            return indexA - indexB;
        });
        
        const niceNames = {
            'timestamp': 'Time',
            'strategy': 'Strategy',
            'ticker': 'Ticker',
            'timeframe': 'TF',
            'total_trades': 'Trades',
            'win_rate': 'Win %',
            'total_profit': 'Net Profit',
            'max_drawdown': 'Max DD (pts)',
            'avg_trade_pl': 'Avg P/L (pts)',
            'entry_ibs': 'Entry IBS',
            'exit_ibs': 'Exit IBS',
            'best_params': 'Best Params',
            'best_profit': 'Best Profit',
            'best_win_rate': 'Best Win %',
            'max_loss_pts': 'Max Loss (pts)',
            'composite_score': 'Score'
        };
        
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = niceNames[header] || header;
            tableHead.appendChild(th);
        });

        // Create Rows
        dataArray.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                let val = row[header];
                if (typeof val === 'number') {
                    val = Number.isInteger(val) ? val : parseFloat(val).toFixed(2);
                }
                td.textContent = val !== null ? val : '';
                tr.appendChild(td);
            });
            tableBody.appendChild(tr);
            
            // Check for Expandable Ledger Data in DB Backtest Runs
            if (rawHeaders.includes('ledger_json') && row['ledger_json']) {
                try {
                    const ledger = JSON.parse(row['ledger_json']);
                    if (ledger && ledger.length > 0) {
                        tr.style.cursor = 'pointer';
                        tr.title = 'Click to expand trade details';
                        
                        // Create the hidden detail row
                        const detailTr = document.createElement('tr');
                        detailTr.style.display = 'none';
                        detailTr.style.backgroundColor = 'var(--bg-dark)';
                        
                        const detailTd = document.createElement('td');
                        detailTd.colSpan = headers.length;
                        detailTd.style.padding = '15px';
                        detailTd.style.background = 'rgba(0,0,0,0.2)';
                        
                        // Calculate Top 5 Wins and Losses
                        const exits = ledger.filter(r => r["P/L Pts"] !== "" && r["P/L Pts"] !== null && !isNaN(parseFloat(r["P/L Pts"])));
                        const sortedExits = exits.map(r => ({...r, pts: parseFloat(r["P/L Pts"])})).sort((a,b) => b.pts - a.pts);
                        
                        const topWins = sortedExits.filter(r => r.pts > 0).slice(0, 5);
                        const topLosses = sortedExits.filter(r => r.pts < 0).reverse().slice(0, 5); // largest losses first
                        
                        if (topWins.length > 0 || topLosses.length > 0) {
                            const statsDiv = document.createElement('div');
                            statsDiv.style.display = 'flex';
                            statsDiv.style.gap = '2rem';
                            statsDiv.style.marginBottom = '1.5rem';
                            
                            const createMiniTable = (title, data, color) => {
                                const container = document.createElement('div');
                                container.style.flex = '1';
                                container.style.background = 'rgba(0,0,0,0.3)';
                                container.style.padding = '10px';
                                container.style.borderRadius = '8px';
                                
                                const h4 = document.createElement('h4');
                                h4.textContent = title;
                                h4.style.marginBottom = '8px';
                                h4.style.color = 'var(--text-main)';
                                h4.style.fontSize = '0.9rem';
                                container.appendChild(h4);
                                
                                if (data.length === 0) {
                                    const p = document.createElement('p');
                                    p.textContent = 'None';
                                    p.style.fontSize = '0.8rem';
                                    p.style.color = 'var(--text-muted)';
                                    container.appendChild(p);
                                    return container;
                                }
                                
                                const t = document.createElement('table');
                                t.style.width = '100%';
                                t.style.borderCollapse = 'collapse';
                                
                                data.forEach(row => {
                                    const tr = document.createElement('tr');
                                    tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                                    
                                    const tdDate = document.createElement('td');
                                    tdDate.textContent = row.Date;
                                    tdDate.style.fontSize = '0.8rem';
                                    tdDate.style.padding = '4px 0';
                                    tdDate.style.color = 'var(--text-muted)';
                                    
                                    const tdPts = document.createElement('td');
                                    tdPts.textContent = (row.pts > 0 ? '+' : '') + row.pts.toFixed(2) + ' pts';
                                    tdPts.style.fontSize = '0.85rem';
                                    tdPts.style.fontWeight = 'bold';
                                    tdPts.style.textAlign = 'right';
                                    tdPts.style.padding = '4px 0';
                                    tdPts.style.color = color;
                                    
                                    tr.appendChild(tdDate);
                                    tr.appendChild(tdPts);
                                    t.appendChild(tr);
                                });
                                container.appendChild(t);
                                return container;
                            };
                            
                            statsDiv.appendChild(createMiniTable('🏆 Top 5 Largest Wins', topWins, 'var(--success)'));
                            statsDiv.appendChild(createMiniTable('💔 Top 5 Largest Losses', topLosses, 'var(--danger)'));
                            detailTd.appendChild(statsDiv);
                        }
                        
                        // Add title for sub-table
                        const title = document.createElement('h4');
                        title.textContent = "Trade Ledger Details";
                        title.style.margin = "0 0 10px 0";
                        title.style.color = "var(--accent-1)";
                        title.style.fontSize = "0.9rem";
                        detailTd.appendChild(title);
                        
                        // Build the sub-table
                        const subTable = document.createElement('table');
                        subTable.className = 'data-table';
                        subTable.style.width = '100%';
                        subTable.style.margin = '0';
                        subTable.style.background = 'rgba(0,0,0,0.3)';
                        subTable.style.borderRadius = '8px';
                        subTable.style.overflow = 'hidden';
                        
                        const rawLedgerHeaders = Object.keys(ledger[0]);
                        const hiddenLedgerCols = ['P/L USD', 'Dollars'];
                        const ledgerHeaders = rawLedgerHeaders.filter(h => !hiddenLedgerCols.includes(h));
                        const subThead = document.createElement('thead');
                        const subHtr = document.createElement('tr');
                        ledgerHeaders.forEach(h => {
                            const th = document.createElement('th');
                            th.textContent = h;
                            th.style.fontSize = '0.75rem';
                            th.style.color = 'var(--text-dim)';
                            th.style.background = 'rgba(0,0,0,0.4)';
                            th.style.padding = '8px 10px';
                            th.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                            subHtr.appendChild(th);
                        });
                        subThead.appendChild(subHtr);
                        subTable.appendChild(subThead);
                        
                        const subTbody = document.createElement('tbody');
                        ledger.forEach(lRow => {
                            const subBtr = document.createElement('tr');
                            ledgerHeaders.forEach(h => {
                                const td = document.createElement('td');
                                let val = lRow[h];
                                if (typeof val === 'number') {
                                    val = Number.isInteger(val) ? val : parseFloat(val).toFixed(2);
                                }
                                td.textContent = val !== null ? val : '';
                                td.style.fontSize = '0.8rem';
                                td.style.padding = '6px 10px';
                                td.style.borderBottom = '1px solid rgba(255,255,255,0.02)';
                                subBtr.appendChild(td);
                            });
                            subTbody.appendChild(subBtr);
                        });
                        subTable.appendChild(subTbody);
                        detailTd.appendChild(subTable);
                        detailTr.appendChild(detailTd);
                        
                        // Toggle logic
                        tr.addEventListener('click', () => {
                            if (detailTr.style.display === 'none') {
                                detailTr.style.display = 'table-row';
                                tr.style.backgroundColor = 'rgba(255,255,255,0.05)';
                            } else {
                                detailTr.style.display = 'none';
                                tr.style.backgroundColor = '';
                            }
                        });
                        
                        tableBody.appendChild(detailTr);
                    }
                } catch (e) {
                    console.log("Failed to parse ledger_json", e);
                }
            }
        });

        // Add Total Row if it is a backtest ledger (contains P/L Pts)
        if (headers.includes("P/L Pts") && !rawHeaders.includes('ledger_json')) {
            const tfoot = document.createElement('tr');
            tfoot.style.fontWeight = 'bold';
            tfoot.style.background = 'rgba(255, 255, 255, 0.05)';
            tfoot.style.borderTop = '2px solid rgba(255,255,255,0.2)';
            
            headers.forEach(header => {
                const td = document.createElement('td');
                if (header === "Date") {
                    td.textContent = "TOTAL";
                } else if (header === "P/L Pts" || header === "Profit %") {
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
    };

    // --- CSV Export ---
    exportBtn?.addEventListener('click', () => {
        if (!window.currentTableData || window.currentTableData.length === 0) {
            window.logToTerminal("No data to export.", "error");
            return;
        }
        
        const keys = Object.keys(window.currentTableData[0]);
        const csvRows = [];
        csvRows.push(keys.join(','));
        
        for (const row of window.currentTableData) {
            const values = keys.map(key => {
                const escape = ('' + (row[key] || '')).replace(/"/g, '""');
                return `"${escape}"`;
            });
            csvRows.push(values.join(','));
        }
        
        const csvString = csvRows.join('\n');
        const blob = new Blob([csvString], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `antigravity_export_${new Date().getTime()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    });

    // --- Switch Workspace Tabs (IBS Mean Reversion vs Day Trading vs Database) ---
    const stratTabs = document.querySelectorAll('.strat-tab');
    const ibsPanel = document.getElementById('ibs-strat-panel');
    const newPanel = document.getElementById('new-strat-panel');
    const dbPanel = document.getElementById('db-strat-panel');
    
    stratTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            stratTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            if (tab.dataset.target === 'new-strat') {
                if (ibsPanel) ibsPanel.style.display = 'none';
                if (dbPanel) dbPanel.style.display = 'none';
                if (newPanel) newPanel.style.display = 'block';
                window.logToTerminal("Switched to Day Trading workspace.", "system");
            } else if (tab.dataset.target === 'db-strat') {
                if (ibsPanel) ibsPanel.style.display = 'none';
                if (newPanel) newPanel.style.display = 'none';
                if (dbPanel) dbPanel.style.display = 'block';
                window.logToTerminal("Switched to Database Analytics workspace.", "system");
            } else {
                if (newPanel) newPanel.style.display = 'none';
                if (dbPanel) dbPanel.style.display = 'none';
                if (ibsPanel) ibsPanel.style.display = 'block';
                window.logToTerminal("Switched to IBS Mean Reversion workspace.", "system");
            }
        });
    });

    // --- SQLite Database Analytics Fetchers ---
    const loadDbBtn = document.getElementById('load-db-btn');
    loadDbBtn?.addEventListener('click', async () => {
        window.logToTerminal('Querying SQLite Database for Live Trades...', 'system');
        try {
            const res = await fetch('/api/db/trades');
            const data = await res.json();
            if (data.status === 'success') {
                if (data.data && data.data.length > 0) {
                    window.currentTableData = data.data;
                    window.renderTable(data.data);
                    window.switchTab('data-table');
                    window.logToTerminal(`SUCCESS: Loaded ${data.data.length} trades from database.`, 'success');
                } else {
                    window.logToTerminal('No trades found in the database yet.', 'system');
                }
            } else {
                window.logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    const loadDbBacktestsBtn = document.getElementById('load-db-backtests-btn');
    loadDbBacktestsBtn?.addEventListener('click', async () => {
        window.logToTerminal('Querying SQLite for Backtest Results...', 'system');
        try {
            const res = await fetch('/api/db/backtests');
            const data = await res.json();
            if (data.status === 'success') {
                if (data.data && data.data.length > 0) {
                    window.currentTableData = data.data;
                    window.renderTable(data.data);
                    window.switchTab('data-table');
                    window.logToTerminal(`SUCCESS: Loaded ${data.data.length} backtest summaries from database.`, 'success');
                } else {
                    window.logToTerminal('No backtests found in the database yet.', 'system');
                }
            } else {
                window.logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    const loadDbOptimizationsBtn = document.getElementById('load-db-optimizations-btn');
    loadDbOptimizationsBtn?.addEventListener('click', async () => {
        window.logToTerminal('Querying SQLite for Optimizer Runs...', 'system');
        try {
            const res = await fetch('/api/db/optimizations');
            const data = await res.json();
            if (data.status === 'success') {
                if (data.data && data.data.length > 0) {
                    window.currentTableData = data.data;
                    window.renderTable(data.data);
                    window.switchTab('data-table');
                    window.logToTerminal(`SUCCESS: Loaded ${data.data.length} optimizer runs from database.`, 'success');
                } else {
                    window.logToTerminal('No optimizer runs found in the database yet.', 'system');
                }
            } else {
                window.logToTerminal(`Error: ${data.message}`, 'error');
            }
        } catch (err) {
            window.logToTerminal(`Network Error: ${err.message}`, 'error');
        }
    });

    window.logToTerminal("Antigravity Core Unified UI Framework Initialized.", "system");
    window.logToTerminal("Awaiting user command...", "system");
});
