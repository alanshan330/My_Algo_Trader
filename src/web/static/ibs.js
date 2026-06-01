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
        const isBlended = document.getElementById('strategy').value.includes('Blended');
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
            entry_ibs_b: isBlended ? (parseFloat(document.getElementById('entry_ibs_b').value) || 0.24) : null,
            exit_ibs_b:  isBlended ? (parseFloat(document.getElementById('exit_ibs_b').value)  || 0.85) : null,
            max_hold_days: parseInt(document.getElementById('max_hold_days').value) || 0,
            max_contracts: parseInt(document.getElementById('max_contracts').value) || 0,
            trend_filter: document.getElementById('trend_filter').checked
        };
    }

    // --- Show/hide Leg B panel and relabel Leg A on strategy change ---
    function updateBlendUI() {
        const isBlended = document.getElementById('strategy').value.includes('Blended');
        const legBRow = document.getElementById('blend-leg-b-row');
        const entryLabel = document.getElementById('entry-ibs-label');
        const exitLabel  = document.getElementById('exit-ibs-label');
        if (legBRow) legBRow.style.display = isBlended ? 'flex' : 'none';
        if (entryLabel) entryLabel.textContent = isBlended ? 'Leg A Entry IBS (Core)' : 'Entry IBS';
        if (exitLabel)  exitLabel.textContent  = isBlended ? 'Leg A Exit IBS (Core)'  : 'Exit IBS';
    }
    document.getElementById('strategy')?.addEventListener('change', updateBlendUI);
    updateBlendUI(); // run once on load

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

                    // Always clear any old blend summary panel first
                    const existingPanel = document.getElementById('blend-summary-panel');
                    if (existingPanel) existingPanel.remove();

                    if (data.blend_summary) {
                        const bs = data.blend_summary;
                        const panel = document.createElement('div');
                        panel.id = 'blend-summary-panel';
                        panel.style.cssText = 'display:flex; gap:1rem; margin-bottom:1rem; flex-wrap:wrap;';

                        const makeCard = (leg) => {
                            const isA = leg.label.includes('Leg A');
                            const accent = isA ? '#38bdf8' : '#a78bfa';
                            const bg    = isA ? 'rgba(56,189,248,0.07)' : 'rgba(167,139,250,0.07)';
                            const border= isA ? 'rgba(56,189,248,0.3)'  : 'rgba(167,139,250,0.3)';
                            const card = document.createElement('div');
                            card.style.cssText = `flex:1; min-width:220px; background:${bg}; border:1px solid ${border}; border-radius:12px; padding:1rem 1.2rem;`;
                            card.innerHTML = `
                                <div style="font-size:0.75rem; font-weight:700; color:${accent}; letter-spacing:0.08em; margin-bottom:0.6rem; text-transform:uppercase;">${leg.label}</div>
                                <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                                    <tr><td style="padding:3px 0; color:#9ca3af;">Trades</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${leg.trades} <span style="color:#9ca3af; font-size:0.75rem;">(${leg.wins}W / ${leg.losses}L)</span></td></tr>
                                    <tr><td style="padding:3px 0; color:#9ca3af;">Win Rate</td><td style="text-align:right; font-weight:600; color:#34d399;">${leg.win_rate}%</td></tr>
                                    <tr><td style="padding:3px 0; color:#9ca3af;">Total Points</td><td style="text-align:right; font-weight:600; color:#34d399;">${leg.total_pts >= 0 ? '+' : ''}${leg.total_pts}</td></tr>
                                    <tr><td style="padding:3px 0; color:#9ca3af;">Avg Per Trade</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${leg.avg_pts >= 0 ? '+' : ''}${leg.avg_pts} pts</td></tr>
                                    <tr><td style="padding:3px 0; color:#9ca3af;">Max Loss</td><td style="text-align:right; font-weight:600; color:#f87171;">${leg.max_loss_pts} pts</td></tr>
                                </table>`;
                            return card;
                        };

                        // Combined total card
                        const totalPts = bs.leg_a.total_pts + bs.leg_b.total_pts;
                        const totalTrades = bs.leg_a.trades + bs.leg_b.trades;
                        const totalWins = bs.leg_a.wins + bs.leg_b.wins;
                        const combined = document.createElement('div');
                        combined.style.cssText = 'flex:1; min-width:220px; background:rgba(251,191,36,0.07); border:1px solid rgba(251,191,36,0.3); border-radius:12px; padding:1rem 1.2rem;';
                        combined.innerHTML = `
                            <div style="font-size:0.75rem; font-weight:700; color:#fbbf24; letter-spacing:0.08em; margin-bottom:0.6rem; text-transform:uppercase;">⚡ Combined Blend</div>
                            <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                                <tr><td style="padding:3px 0; color:#9ca3af;">Total Trades</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${totalTrades} <span style="color:#9ca3af; font-size:0.75rem;">(${totalWins}W)</span></td></tr>
                                <tr><td style="padding:3px 0; color:#9ca3af;">Blended Win Rate</td><td style="text-align:right; font-weight:600; color:#34d399;">${totalTrades > 0 ? (totalWins/totalTrades*100).toFixed(1) : 0}%</td></tr>
                                <tr><td style="padding:3px 0; color:#9ca3af;">Combined Points</td><td style="text-align:right; font-weight:600; color:#34d399;">${totalPts >= 0 ? '+' : ''}${totalPts.toFixed(1)}</td></tr>
                                <tr><td style="padding:3px 0; color:#9ca3af;">Avg Per Trade</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${totalTrades > 0 ? (totalPts/totalTrades >= 0 ? '+' : '') + (totalPts/totalTrades).toFixed(1) : 0} pts</td></tr>
                                <tr><td style="padding:3px 0; color:#9ca3af;">Leg A : Leg B Trades</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${bs.leg_a.trades} : ${bs.leg_b.trades}</td></tr>
                            </table>`;

                        panel.appendChild(makeCard(bs.leg_a));
                        panel.appendChild(makeCard(bs.leg_b));
                        panel.appendChild(combined);

                        const tableContainer = document.querySelector('.table-container');
                        if (tableContainer) tableContainer.parentElement.insertBefore(panel, tableContainer);
                    }

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
                window.logToTerminal('This may take 30-60 seconds. Please wait...', 'system');
                window.switchTab('terminal');
                
                // 5-minute timeout for the optimizer
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 300000);
                
                try {
                    const res = await fetch('/api/optimize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(params),
                        signal: controller.signal
                    });
                    clearTimeout(timeoutId);
                    const data = await res.json();
                    
                    if (data.status === 'success') {
                        window.logToTerminal(data.output, 'success');
                        window.lastBacktestSource = 'ibs';
                        
                        // Always clear old panels
                        const oldPanel = document.getElementById('blend-summary-panel');
                        if (oldPanel) oldPanel.remove();
                        const oldOptPanel = document.getElementById('optimizer-summary-panel');
                        if (oldOptPanel) oldOptPanel.remove();
                        
                        if (data.data && data.data.length > 0) {
                            window.currentTableData = data.data;
                            window.renderTable(data.data);
                            
                            // --- Optimizer Summary Cards ---
                            const sorted = [...data.data].sort((a, b) => b.composite_score - a.composite_score);
                            const best = sorted[0];
                            const runner = sorted.length > 1 ? sorted[1] : null;
                            
                            const panel = document.createElement('div');
                            panel.id = 'optimizer-summary-panel';
                            panel.style.cssText = 'display:flex; gap:1rem; margin-bottom:1rem; flex-wrap:wrap;';
                            
                            // Helper: render score breakdown bar (handles both single & blend scoring)
                            const scoreBar = (c, scoreKey) => {
                                const total = (c[scoreKey]||0).toFixed(1);
                                const isBlend = c.s_retdd !== undefined;
                                
                                let segments, labels;
                                if (isBlend) {
                                    // Blend scoring: 25 Ret/DD + 20 Profit + 15 Diversity + 15 WR + 15 Avg + 10 Risk
                                    const s = { rd: c.s_retdd||0, p: c.s_profit||0, d: c.s_diversity||0, w: c.s_winrate||0, a: c.s_avg||0, r: c.s_risk||0 };
                                    segments = `
                                        <div style="width:${s.rd}%; background:#2dd4bf;" title="Ret/DD: ${s.rd}/25"></div>
                                        <div style="width:${s.p}%; background:#34d399;" title="Profit: ${s.p}/20"></div>
                                        <div style="width:${s.d}%; background:#fb923c;" title="Diversity: ${s.d}/15"></div>
                                        <div style="width:${s.w}%; background:#fbbf24;" title="Win Rate: ${s.w}/15"></div>
                                        <div style="width:${s.a}%; background:#60a5fa;" title="Avg/Trade: ${s.a}/15"></div>
                                        <div style="width:${s.r}%; background:#f87171;" title="Risk: ${s.r}/10"></div>`;
                                    labels = `
                                        <span style="color:#2dd4bf;">RD:${s.rd}</span>
                                        <span style="color:#34d399;">P:${s.p}</span>
                                        <span style="color:#fb923c;">D:${s.d}</span>
                                        <span style="color:#fbbf24;">W:${s.w}</span>
                                        <span style="color:#60a5fa;">A:${s.a}</span>
                                        <span style="color:#f87171;">R:${s.r}</span>`;
                                } else {
                                    // Single-combo scoring: 35 Profit + 15 Avg + 20 Risk + 20 WR + 10 Exposure
                                    const s = { p: c.s_profit||0, a: c.s_avg||0, r: c.s_risk||0, w: c.s_winrate||0, e: c.s_exposure||0 };
                                    segments = `
                                        <div style="width:${s.p}%; background:#34d399;" title="Profit: ${s.p}/35"></div>
                                        <div style="width:${s.a}%; background:#60a5fa;" title="Avg/Trade: ${s.a}/15"></div>
                                        <div style="width:${s.r}%; background:#f87171;" title="Risk: ${s.r}/20"></div>
                                        <div style="width:${s.w}%; background:#fbbf24;" title="Win Rate: ${s.w}/20"></div>
                                        <div style="width:${s.e}%; background:#a78bfa;" title="Exposure: ${s.e}/10"></div>`;
                                    labels = `
                                        <span style="color:#34d399;">P:${s.p}</span>
                                        <span style="color:#60a5fa;">A:${s.a}</span>
                                        <span style="color:#f87171;">R:${s.r}</span>
                                        <span style="color:#fbbf24;">W:${s.w}</span>
                                        <span style="color:#a78bfa;">E:${s.e}</span>`;
                                }
                                
                                return `
                                    <div style="margin-top:0.5rem; padding-top:0.4rem; border-top:1px solid rgba(255,255,255,0.08);">
                                        <div style="display:flex; justify-content:space-between; font-size:0.65rem; color:#9ca3af; margin-bottom:3px;">
                                            <span>Score Breakdown</span><span style="color:#f1f5f9; font-weight:700;">${total}/100</span>
                                        </div>
                                        <div style="display:flex; height:6px; border-radius:3px; overflow:hidden; gap:1px;">
                                            ${segments}
                                        </div>
                                        <div style="display:flex; justify-content:space-between; font-size:0.58rem; color:#6b7280; margin-top:2px;">
                                            ${labels}
                                        </div>
                                    </div>`;
                            };

                            const makeOptCard = (combo, title, accent, bg, border, emoji) => {
                                const card = document.createElement('div');
                                card.style.cssText = `flex:1; min-width:220px; background:${bg}; border:1px solid ${border}; border-radius:12px; padding:1rem 1.2rem;`;
                                card.innerHTML = `
                                    <div style="font-size:0.75rem; font-weight:700; color:${accent}; letter-spacing:0.08em; margin-bottom:0.6rem; text-transform:uppercase;">${emoji} ${title}</div>
                                    <div style="display:flex; gap:0.8rem; margin-bottom:0.6rem;">
                                        <div style="background:rgba(255,255,255,0.06); border-radius:8px; padding:0.5rem 0.7rem; text-align:center; flex:1;">
                                            <div style="font-size:0.65rem; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em;">Entry IBS</div>
                                            <div style="font-size:1.3rem; font-weight:800; color:${accent};">${combo.entry.toFixed(2)}</div>
                                        </div>
                                        <div style="background:rgba(255,255,255,0.06); border-radius:8px; padding:0.5rem 0.7rem; text-align:center; flex:1;">
                                            <div style="font-size:0.65rem; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em;">Exit IBS</div>
                                            <div style="font-size:1.3rem; font-weight:800; color:${accent};">${combo.exit.toFixed(2)}</div>
                                        </div>
                                    </div>
                                    <table style="width:100%; border-collapse:collapse; font-size:0.82rem;">
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Trades</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${combo.trades}</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Win Rate</td><td style="text-align:right; font-weight:600; color:#34d399;">${combo.win_rate.toFixed(1)}%</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Total Points</td><td style="text-align:right; font-weight:600; color:#34d399;">${combo.total_pts >= 0 ? '+' : ''}${combo.total_pts.toFixed(1)}</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Avg Per Trade</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${combo.avg_pts.toFixed(1)} pts</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Max Loss</td><td style="text-align:right; font-weight:600; color:#f87171;">${combo.max_loss.toFixed(1)} pts</td></tr>
                                    </table>
                                    ${scoreBar(combo, 'composite_score')}`;
                                return card;
                            };
                            
                            // Card 1: Best Combo
                            panel.appendChild(makeOptCard(best, 'Best Combo (#1)', '#38bdf8', 'rgba(56,189,248,0.07)', 'rgba(56,189,248,0.3)', '🏆'));
                            
                            // Card 2: Runner Up
                            if (runner) {
                                panel.appendChild(makeOptCard(runner, 'Runner Up (#2)', '#a78bfa', 'rgba(167,139,250,0.07)', 'rgba(167,139,250,0.3)', '🥈'));
                            }
                            
                            // Card 3: Best Scored Blend (from actual blend pair optimization)
                            const blendData = data.blend_data;
                            if (blendData && blendData.length > 0) {
                                const topBlend = blendData[0]; // Already sorted by blend_score from backend
                                const blendCard = document.createElement('div');
                                blendCard.style.cssText = 'flex:1; min-width:220px; background:rgba(251,191,36,0.07); border:1px solid rgba(251,191,36,0.3); border-radius:12px; padding:1rem 1.2rem;';
                                
                                blendCard.innerHTML = `
                                    <div style="font-size:0.75rem; font-weight:700; color:#fbbf24; letter-spacing:0.08em; margin-bottom:0.6rem; text-transform:uppercase;">⚡ Best Scored Blend</div>
                                    <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem;">
                                        <div style="flex:1; background:rgba(56,189,248,0.1); border-radius:8px; padding:0.4rem 0.5rem; text-align:center;">
                                            <div style="font-size:0.6rem; color:#38bdf8; font-weight:600;">CORE</div>
                                            <div style="font-size:1.1rem; font-weight:800; color:#38bdf8;">${topBlend.core_entry.toFixed(2)}/${topBlend.core_exit.toFixed(2)}</div>
                                        </div>
                                        <div style="flex:1; background:rgba(167,139,250,0.1); border-radius:8px; padding:0.4rem 0.5rem; text-align:center;">
                                            <div style="font-size:0.6rem; color:#a78bfa; font-weight:600;">DEEP DIP</div>
                                            <div style="font-size:1.1rem; font-weight:800; color:#a78bfa;">${topBlend.dd_entry.toFixed(2)}/${topBlend.dd_exit.toFixed(2)}</div>
                                        </div>
                                    </div>
                                    <table style="width:100%; border-collapse:collapse; font-size:0.82rem;">
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Combined Trades</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${topBlend.trades}</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Win Rate</td><td style="text-align:right; font-weight:600; color:#34d399;">${topBlend.win_rate.toFixed(1)}%</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Total Points</td><td style="text-align:right; font-weight:600; color:#34d399;">${topBlend.total_pts >= 0 ? '+' : ''}${topBlend.total_pts.toFixed(1)}</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Avg Per Trade</td><td style="text-align:right; font-weight:600; color:#f1f5f9;">${topBlend.avg_pts.toFixed(1)} pts</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Max Loss</td><td style="text-align:right; font-weight:600; color:#f87171;">${topBlend.max_loss.toFixed(1)} pts</td></tr>
                                    </table>
                                    ${scoreBar(topBlend, 'blend_score')}`;
                                panel.appendChild(blendCard);
                            } else if (runner) {
                                // Fallback: simple estimated blend if no blend_data available
                                const blendCard = document.createElement('div');
                                blendCard.style.cssText = 'flex:1; min-width:220px; background:rgba(251,191,36,0.07); border:1px solid rgba(251,191,36,0.3); border-radius:12px; padding:1rem 1.2rem;';
                                const combinedPts = best.total_pts + runner.total_pts;
                                blendCard.innerHTML = `
                                    <div style="font-size:0.75rem; font-weight:700; color:#fbbf24; letter-spacing:0.08em; margin-bottom:0.6rem; text-transform:uppercase;">⚡ Est. Blend (#1 + #2)</div>
                                    <table style="width:100%; border-collapse:collapse; font-size:0.82rem;">
                                        <tr><td style="padding:3px 0; color:#38bdf8; font-weight:600;">Core</td><td style="text-align:right; color:#f1f5f9; font-weight:700;">${best.entry.toFixed(2)}/${best.exit.toFixed(2)}</td></tr>
                                        <tr><td style="padding:3px 0; color:#a78bfa; font-weight:600;">Deep Dip</td><td style="text-align:right; color:#f1f5f9; font-weight:700;">${runner.entry.toFixed(2)}/${runner.exit.toFixed(2)}</td></tr>
                                        <tr><td style="padding:2px 0; color:#9ca3af;">Est. Combined Pts</td><td style="text-align:right; font-weight:600; color:#34d399;">${combinedPts >= 0 ? '+' : ''}${combinedPts.toFixed(1)}</td></tr>
                                    </table>`;
                                panel.appendChild(blendCard);
                            }
                            
                            const tableContainer = document.querySelector('.table-container');
                            if (tableContainer) tableContainer.parentElement.insertBefore(panel, tableContainer);
                            
                            window.switchTab('data-table');
                        }
                    } else {
                        window.logToTerminal(`Error: ${data.message}`, 'error');
                    }
                } catch (fetchErr) {
                    clearTimeout(timeoutId);
                    if (fetchErr.name === 'AbortError') {
                        window.logToTerminal('Optimizer timed out after 5 minutes. Try a shorter date range or fewer combos.', 'error');
                    } else {
                        window.logToTerminal(`Connection Error: Make sure the server is running (python -m src.web.app). Details: ${fetchErr.message}`, 'error');
                    }
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
