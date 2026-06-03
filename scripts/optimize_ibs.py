"""
IBS Parameter Optimizer
-----------------------
Runs a grid search over IBS entry and exit thresholds for the past 5 years.
Requires TWS to be running (port 7497) OR a CSV file to be provided.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ─── Configuration ─────────────────────────────────────────────────────────────
SYMBOL        = "NQ"          # Change to your ticker
YEARS         = 5             # How many years of history to test
CSV_PATH      = ""            # Leave blank to pull from IBKR TWS

STRATEGY_MODE = "Average Down" # "Single Entry" or "Average Down"
TREND_FILTER  = False          # Enable 200-SMA filter
MAX_HOLD_DAYS = 0              # 0 = unlimited
MAX_CONTRACTS = 3              # 0 = unlimited

# Grid search ranges
ENTRY_VALUES  = [round(x, 2) for x in np.arange(0.12, 0.36, 0.01)]  # 0.12 to 0.35 (step 0.01)
EXIT_VALUES   = [round(x, 2) for x in np.arange(0.70, 0.96, 0.01)]  # 0.70 to 0.95 (step 0.01)
# ───────────────────────────────────────────────────────────────────────────────


def fetch_data(symbol, start_date_str, end_date_str, csv_path):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    except Exception:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 5)

    if csv_path and os.path.exists(csv_path):
        print(f"Loading from CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        rename_map = {}
        for col in df.columns:
            lc = col.strip().lower()
            if lc in ['time','date']: rename_map[col] = 'Date'
            elif lc == 'open':        rename_map[col] = 'Open'
            elif lc == 'high':        rename_map[col] = 'High'
            elif lc == 'low':         rename_map[col] = 'Low'
            elif lc == 'close':       rename_map[col] = 'Close'
        df.rename(columns=rename_map, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df, start_date, end_date

    print(f"Connecting to IBKR TWS to fetch {years} years of {symbol} data...")
    import nest_asyncio
    nest_asyncio.apply()
    from ib_insync import IB, ContFuture, Stock, util

    ib = IB()
    try:
        try:
            ib.connect('127.0.0.1', 7497, clientId=10)
        except:
            ib.connect('127.0.0.1', 7496, clientId=10)
    except Exception as e:
        print(f"Connection Error: {e}")
        sys.exit(1)

    futures_list = ["NQ","ES","YM","RTY","CL","GC","BTC","ETH"]
    is_future = any(symbol.upper() == f for f in futures_list)

    if is_future:
        exchange_map = {"YM": "CBOT", "GC": "NYMEX", "CL": "NYMEX"}
        exch = exchange_map.get(symbol.upper(), "CME")
        contract = ContFuture(symbol, exch)
    else:
        contract = Stock(symbol, 'SMART', 'USD')

    ib.qualifyContracts(contract)
    days = (datetime.now() - start_date).days
    duration = f"{max(1, days)} D"
    show_type = 'BID' if is_future else 'TRADES'

    print(f"Requesting {duration} of daily data...")
    bars = ib.reqHistoricalData(
        contract, endDateTime='',
        durationStr=duration,
        barSizeSetting="1 day",
        whatToShow=show_type,
        useRTH=True,
        formatDate=1
    )
    ib.disconnect()

    if not bars:
        print("No data returned from IBKR.")
        sys.exit(1)

    df = util.df(bars)
    df.rename(columns={"date":"Date","open":"Open","high":"High","low":"Low","close":"Close"}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.index = df.index.tz_localize(None)
    df = df[(df.index >= start_date) & (df.index <= end_date)]
    return df, start_date, end_date


def run_backtest(df, entry_thresh, exit_thresh, is_avg_down,
                 trend_filter, max_hold, max_cont, multiplier,
                 atr, sma_200):
    ibs   = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    high  = df['High']
    low   = df['Low']
    close = df['Close']

    contracts_held = 0
    total_cost     = 0.0
    trades         = []
    days_held      = 0
    highest_high   = 0.0
    max_contracts_used = 0

    for i in range(len(df)):
        cur_close = close.iloc[i]
        cur_ibs   = ibs.iloc[i]

        if pd.isna(cur_ibs):
            continue

        if contracts_held > 0:
            days_held += 1

        if cur_ibs < entry_thresh:
            # Filters
            if not is_avg_down and contracts_held > 0:
                pass
            elif trend_filter and cur_close < sma_200.iloc[i]:
                pass
            elif max_cont > 0 and contracts_held >= max_cont:
                pass
            else:
                if contracts_held == 0:
                    highest_high = cur_close
                    days_held = 1
                contracts_held += 1
                if contracts_held > max_contracts_used:
                    max_contracts_used = contracts_held
                total_cost     += cur_close

        elif contracts_held > 0:
            avg_entry = total_cost / contracts_held
            bar_high  = high.iloc[i]
            bar_low   = low.iloc[i]

            if bar_high > highest_high:
                highest_high = bar_high

            exit_price = None
            reason     = None

            # Time-based exit
            if max_hold > 0 and days_held > max_hold:
                exit_price = cur_close
                reason     = "TIME"

            # IBS profit exit
            elif cur_ibs > exit_thresh:
                exit_price = cur_close
                reason     = "IBS"

            if exit_price is not None:
                pts = (exit_price * contracts_held) - total_cost
                pct = ((exit_price - avg_entry) / avg_entry) * 100
                trades.append({
                    "index":      i,
                    "profit_pct": pct,
                    "points":     pts,
                    "dollars":    pts * multiplier,
                    "reason":     reason
                })
                contracts_held = 0
                total_cost     = 0.0
                days_held      = 0

    if not trades:
        return None

    total = len(trades)
    wins  = sum(1 for t in trades if t["profit_pct"] > 0)
    losses = [t["points"] for t in trades if t["points"] < 0]
    max_loss = min(losses) if losses else 0.0
    return {
        "trades":      total,
        "win_rate":    (wins / total) * 100,
        "total_pts":   sum(t["points"] for t in trades),
        "total_usd":   sum(t["dollars"] for t in trades),
        "avg_pts":     sum(t["points"] for t in trades) / total,
        "max_loss":    max_loss,
        "max_contracts": max_contracts_used,
        "trade_list":  trades
    }


def main():
    import json
    state_file = os.path.join(os.path.dirname(__file__), "..", "ui_state.json")
    
    # Defaults
    saved_csv = CSV_PATH
    saved_symbol = SYMBOL
    saved_strategy = STRATEGY_MODE
    saved_trend = TREND_FILTER
    saved_max_hold = MAX_HOLD_DAYS
    saved_max_cont = MAX_CONTRACTS
    saved_start_date = ""
    saved_end_date = ""

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            saved_csv = state.get("csv_path", "") or CSV_PATH
            saved_symbol = state.get("ticker", SYMBOL)
            saved_strategy = state.get("strategy", STRATEGY_MODE)
            saved_trend = state.get("trend_filter", TREND_FILTER)
            saved_max_hold = int(state.get("max_hold_days", MAX_HOLD_DAYS))
            saved_max_cont = int(state.get("max_contracts", MAX_CONTRACTS))
            saved_start_date = state.get("start_date", "")
            saved_end_date = state.get("end_date", "")
    except Exception:
        pass
        
    sym_to_use = saved_symbol.upper()
    
    if saved_csv and not os.path.exists(saved_csv):
        print(f"\nWARNING: The saved CSV path '{saved_csv}' does not exist!")
        print("Falling back to IBKR TWS connection...\n")
    elif not saved_csv:
        print("\nNo CSV path provided. Attempting to connect to IBKR TWS...\n")

    # ── Load data once ──────────────────────────────────────────────────────────
    df, start_date, end_date = fetch_data(sym_to_use, saved_start_date, saved_end_date, saved_csv)
    df = df.dropna()
    for col in ['High','Low','Close']:
        df[col] = pd.to_numeric(df[col])

    # Pre-compute indicators
    tr   = pd.concat([df['High']-df['Low'],
                      (df['High']-df['Close'].shift(1)).abs(),
                      (df['Low'] -df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr     = tr.rolling(14).mean()
    sma_200 = df['Close'].rolling(200).mean()

    # Multiplier
    mult_map = {
        "MNQ": 2, "MES": 5, "MYM": 0.5, "M2K": 5,
        "NQ": 20, "ES": 50, "YM": 5, "RTY": 50,
        "CL": 1000, "GC": 100
    }
    # Check exact match first, then substring
    if sym_to_use in mult_map:
        multiplier = mult_map[sym_to_use]
    else:
        multiplier = next((v for k,v in mult_map.items() if k in sym_to_use), 1)

    is_avg_down = "Average Down" in saved_strategy or "Blended" in saved_strategy
    
    # If max_contracts is 0 (unlimited), use a sensible default for optimization
    # Unlimited contracts inflates drawdowns and produces inconsistent results
    if saved_max_cont == 0:
        saved_max_cont = 3

    total_combos = len(ENTRY_VALUES) * len(EXIT_VALUES)
    print(f"\nRunning {total_combos} parameter combinations...")
    print(f"Symbol: {sym_to_use} | Period: {start_date.date()} to {end_date.date()}")
    print(f"Mode: {saved_strategy} | Trend Filter: {saved_trend} | Max Hold: {saved_max_hold}d | Max Contracts: {saved_max_cont}")

    results = []
    for idx, (entry, exit_) in enumerate(product(ENTRY_VALUES, EXIT_VALUES), 1):
        if entry >= exit_:          # Sanity guard
            continue
        r = run_backtest(df, entry, exit_, is_avg_down,
                         saved_trend, saved_max_hold, saved_max_cont,
                         multiplier, atr, sma_200)
        if r:
            r["entry"] = entry
            r["exit"]  = exit_
            results.append(r)

        if idx % 20 == 0 or idx == total_combos:
            print(f"  Progress: {idx}/{total_combos} combos tested...")

    if not results:
        print("No valid results found.")
        return

    # ── Sort and report ─────────────────────────────────────────────────────────
    highest_pts = max(r["total_pts"] for r in results)
    highest_pts = highest_pts if highest_pts > 0 else 1
    
    smallest_loss_abs = min(abs(r["max_loss"]) for r in results)
    lowest_max_cont = min(r["max_contracts"] for r in results)
    if lowest_max_cont == 0: lowest_max_cont = 1

    highest_avg = max(abs(r["avg_pts"]) for r in results) or 1

    for r in results:
        # Win rate score (30 pts) — consistency is #1
        win_score = (r["win_rate"] / 100.0) * 30.0
        
        # Max loss / risk score (25 pts) — smaller single loss = sleep better
        loss_abs = abs(r["max_loss"])
        if loss_abs == 0:
            loss_score = 25.0
        else:
            loss_score = (max(smallest_loss_abs, 0.01) / max(loss_abs, 0.01)) * 25.0
            loss_score = min(loss_score, 25.0)
        
        # Total profit score (20 pts) — enough profit, not max profit
        profit_score = (r["total_pts"] / highest_pts) * 20 if r["total_pts"] > 0 else 0
        
        # Average trade quality (15 pts)
        avg_score = (r["avg_pts"] / highest_avg) * 15 if r["avg_pts"] > 0 else 0
        
        # Contract exposure score (10 pts) — lower exposure = safer
        cont = max(r["max_contracts"], 1)
        cont_score = (lowest_max_cont / cont) * 10.0
        
        r["composite_score"] = win_score + loss_score + profit_score + avg_score + cont_score
        r["s_winrate"] = round(win_score, 1)
        r["s_risk"] = round(loss_score, 1)
        r["s_profit"] = round(profit_score, 1)
        r["s_avg"] = round(avg_score, 1)
        r["s_exposure"] = round(cont_score, 1)

    results_df = pd.DataFrame(results).sort_values("composite_score", ascending=False)

    print("\n" + "="*80)
    print(f"  IBS PARAMETER OPTIMIZATION RESULTS -- Top 20 Combinations")
    print(f"  Symbol: {sym_to_use} | {start_date.date()} to {end_date.date()} | Mode: {saved_strategy}")
    print("="*80)
    print(f"  {'Rank':<5} {'Score':<7} {'Entry':<8} {'Exit':<8} {'Trades':<8} {'WinRate':<10} {'Total Pts':>10} {'Max Loss':>10}")
    print("  " + "-"*80)

    for rank, (_, row) in enumerate(results_df.head(20).iterrows(), 1):
        print(f"  {rank:<5} {row['composite_score']:<7.1f} {row['entry']:<8.2f} {row['exit']:<8.2f} "
              f"{int(row['trades']):<8} {row['win_rate']:>7.1f}%   "
              f"{row['total_pts']:>10.1f} {row['max_loss']:>10.1f}")

    best = results_df.iloc[0]
    print("\n" + "="*80)
    print(f"  *  BEST PARAMETERS: Entry IBS = {best['entry']:.2f}  |  Exit IBS = {best['exit']:.2f}")
    print(f"     Score: {best['composite_score']:.1f}/100 | {int(best['trades'])} trades | {best['win_rate']:.1f}% win rate | "
          f"{best['total_pts']:+.1f} pts | Max Loss: {best['max_loss']:.1f} pts")
    print("="*80)

    # Save to file
    from datetime import datetime
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(os.path.dirname(__file__), "..", "results", f"ibs_optimization_report_{stamp}.csv")
    results_df.to_csv(out_path, index=False)
    print(f"\n  Full results saved to: {os.path.basename(out_path)}")
    
    # ── Blend Pair Optimization ──────────────────────────────────────────────────
    # Select diverse candidates (best at each entry level) and score pairs
    # by Return/Drawdown ratio and entry diversity — not just raw profit.
    if "Blended" in saved_strategy:
        print("\n" + "="*80)
        print("  BLEND PAIR OPTIMIZATION -- Finding uncorrelated Core + Deep Dip pairs...")
        print("="*80)
        
        # Step 1: Pick the best combo at EACH unique entry level for diversity
        candidates = []
        for entry_val in sorted(results_df['entry'].unique()):
            subset = results_df[results_df['entry'] == entry_val]
            best_at_entry = subset.iloc[0]
            candidates.append(best_at_entry.to_dict())
        
        print(f"  Selected {len(candidates)} diverse candidates (best per entry level)")
        
        # Step 2: Test all pairs where Core entry > Deep Dip entry
        blend_results = []
        pair_count = 0
        for i, core in enumerate(candidates):
            for j, dd in enumerate(candidates):
                if i == j:
                    continue
                if core['entry'] == dd['entry']:
                    continue
                # Core = wider entry (higher), Deep Dip = tighter entry (lower)
                if core['entry'] < dd['entry']:
                    continue
                # Require meaningful separation between the two legs
                if core['entry'] - dd['entry'] < 0.05:
                    continue
                    
                r_core = run_backtest(df, core['entry'], core['exit'], True,
                                     saved_trend, saved_max_hold, saved_max_cont,
                                     multiplier, atr, sma_200)
                r_dd = run_backtest(df, dd['entry'], dd['exit'], True,
                                   saved_trend, saved_max_hold, saved_max_cont,
                                   multiplier, atr, sma_200)
                
                if not r_core or not r_dd:
                    continue
                
                total_trades = r_core['trades'] + r_dd['trades']
                total_pts = r_core['total_pts'] + r_dd['total_pts']
                total_usd = r_core['total_usd'] + r_dd['total_usd']
                wins_core = int(r_core['trades'] * r_core['win_rate'] / 100)
                wins_dd = int(r_dd['trades'] * r_dd['win_rate'] / 100)
                combined_wr = ((wins_core + wins_dd) / total_trades * 100) if total_trades > 0 else 0
                combined_avg = total_pts / total_trades if total_trades > 0 else 0
                
                # Calculate true peak-to-trough combined drawdown
                all_trades = r_core['trade_list'] + r_dd['trade_list']
                all_trades.sort(key=lambda t: t['index'])
                equity = 0.0
                peak_equity = 0.0
                max_dd = 0.0
                for t in all_trades:
                    equity += t['points']
                    if equity > peak_equity:
                        peak_equity = equity
                    drawdown = peak_equity - equity
                    if drawdown > max_dd:
                        max_dd = drawdown
                        
                # Ensure we have a valid non-zero drawdown for ratio math
                combined_max_loss = -max_dd if max_dd > 0 else -1.0
                
                combined_max_cont = max(r_core['max_contracts'], r_dd['max_contracts'])
                
                dd_abs = abs(combined_max_loss) if combined_max_loss != 0 else 1
                ret_dd_ratio = total_pts / dd_abs
                entry_spread = abs(core['entry'] - dd['entry'])
                
                blend_results.append({
                    'core_entry': core['entry'],
                    'core_exit': core['exit'],
                    'dd_entry': dd['entry'],
                    'dd_exit': dd['exit'],
                    'trades': total_trades,
                    'win_rate': combined_wr,
                    'total_pts': total_pts,
                    'total_usd': total_usd,
                    'avg_pts': combined_avg,
                    'max_loss': combined_max_loss,
                    'max_contracts': combined_max_cont,
                    'ret_dd_ratio': ret_dd_ratio,
                    'entry_spread': entry_spread,
                })
                pair_count += 1
        
        print(f"  Tested {pair_count} blend pairs.")
        
        if blend_results:
            # Blend scoring: consistency-first (WR + risk control + trade frequency)
            b_highest_pts = max(r['total_pts'] for r in blend_results)
            b_highest_pts = b_highest_pts if b_highest_pts > 0 else 1
            b_highest_ratio = max(r['ret_dd_ratio'] for r in blend_results)
            b_highest_ratio = b_highest_ratio if b_highest_ratio > 0 else 1
            b_max_spread = max(r['entry_spread'] for r in blend_results) or 0.01
            b_smallest_loss = min(abs(r['max_loss']) for r in blend_results)
            b_highest_avg = max(abs(r['avg_pts']) for r in blend_results) or 1
            b_most_trades = max(r['trades'] for r in blend_results) or 1
            
            for r in blend_results:
                # Win rate (25 pts) — consistency is king
                win_score = (r['win_rate'] / 100.0) * 25
                
                # Max loss / risk (20 pts) — smaller worst-case loss
                loss_abs = abs(r['max_loss'])
                if loss_abs == 0:
                    loss_score = 20.0
                else:
                    loss_score = (max(b_smallest_loss, 0.01) / max(loss_abs, 0.01)) * 20.0
                    loss_score = min(loss_score, 20.0)
                
                # Return/Drawdown ratio (15 pts) — still valuable, not dominant
                ratio_score = (r['ret_dd_ratio'] / b_highest_ratio) * 15 if r['ret_dd_ratio'] > 0 else 0
                
                # Trade count (15 pts) — more trades = steadier income
                trade_score = (r['trades'] / b_most_trades) * 15
                
                # Entry diversity (15 pts) — the point of blending
                diversity_score = (r['entry_spread'] / b_max_spread) * 15
                
                # Avg trade quality (10 pts)
                avg_score = (r['avg_pts'] / b_highest_avg) * 10 if r['avg_pts'] > 0 else 0
                
                r['blend_score'] = win_score + loss_score + ratio_score + trade_score + diversity_score + avg_score
                r['s_winrate'] = round(win_score, 1)
                r['s_risk'] = round(loss_score, 1)
                r['s_retdd'] = round(ratio_score, 1)
                r['s_trades'] = round(trade_score, 1)
                r['s_diversity'] = round(diversity_score, 1)
                r['s_avg'] = round(avg_score, 1)
            
            blend_df = pd.DataFrame(blend_results).sort_values('blend_score', ascending=False).head(10)
            
            print(f"\n  {'Rank':<5} {'Score':<7} {'Core':<12} {'DeepDip':<12} {'Trades':<8} {'WR%':<8} {'TotalPts':>10} {'Ret/DD':>8} {'Spread':>6}")
            print("  " + "-"*85)
            for rank, (_, row) in enumerate(blend_df.head(10).iterrows(), 1):
                core_str = f"{row['core_entry']:.2f}/{row['core_exit']:.2f}"
                dd_str = f"{row['dd_entry']:.2f}/{row['dd_exit']:.2f}"
                print(f"  {rank:<5} {row['blend_score']:<7.1f} {core_str:<12} {dd_str:<12} "
                      f"{int(row['trades']):<8} {row['win_rate']:>5.1f}%  "
                      f"{row['total_pts']:>10.1f} {row['ret_dd_ratio']:>7.1f}x  {row['entry_spread']:>5.2f}")
            
            bb = blend_df.iloc[0]
            print("\n" + "="*80)
            print(f"  >> BEST BLEND: Core ({bb['core_entry']:.2f}/{bb['core_exit']:.2f}) + Deep Dip ({bb['dd_entry']:.2f}/{bb['dd_exit']:.2f})")
            print(f"     Score: {bb['blend_score']:.1f}/100 | {int(bb['trades'])} trades | {bb['win_rate']:.1f}% WR | "
                  f"{bb['total_pts']:+.1f} pts | Ret/DD: {bb['ret_dd_ratio']:.1f}x | Entry Spread: {bb['entry_spread']:.2f}")
            print("="*80)
            
            blend_path = os.path.join(os.path.dirname(__file__), "..", "results", f"ibs_blend_report_{stamp}.csv")
            blend_df.to_csv(blend_path, index=False)
            print(f"\n  Blend results saved to: {os.path.basename(blend_path)}")
    
    # Log to Database
    try:
        from src.trading import db
        params_str = f"Entry: {best['entry']:.2f}, Exit: {best['exit']:.2f}"
        db.log_optimizer_run(
            strategy=saved_strategy,
            ticker=sym_to_use,
            timeframe="1 day",
            best_params=params_str,
            best_profit=best['total_usd'],
            best_win_rate=best['win_rate'],
            max_loss_pts=best['max_loss'],
            composite_score=best['composite_score']
        )
    except Exception as e:
        print(f"Failed to log to database: {e}")
    
    # We will let the web UI handle displaying the results


if __name__ == "__main__":
    main()
