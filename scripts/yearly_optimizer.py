import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from itertools import product
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.optimize_ibs import fetch_data, run_backtest

def main():
    state_file = os.path.join(os.path.dirname(__file__), "..", "ui_state.json")
    
    # Defaults
    saved_csv = ""
    saved_symbol = "NQ"
    saved_strategy = "Average Down"
    saved_trend = False
    saved_max_hold = 0
    saved_max_cont = 3

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            saved_csv = state.get("csv_path", "")
            saved_symbol = state.get("ticker", "NQ")
            saved_strategy = state.get("strategy", "Average Down")
            saved_trend = state.get("trend_filter", False)
            saved_max_hold = int(state.get("max_hold_days", 0))
            saved_max_cont = int(state.get("max_contracts", 3))
    except Exception:
        pass
        
    sym_to_use = saved_symbol.upper()

    if not saved_csv or not os.path.exists(saved_csv):
        print("Please set a valid CSV file in the UI first.")
        return

    # Load full dataset
    df, _, _ = fetch_data(sym_to_use, "2020-01-01", "2026-01-01", saved_csv)
    df = df.dropna()
    for col in ['High','Low','Close']:
        df[col] = pd.to_numeric(df[col])

    # Pre-compute indicators on full dataset
    tr   = pd.concat([df['High']-df['Low'],
                      (df['High']-df['Close'].shift(1)).abs(),
                      (df['Low'] -df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    full_atr     = tr.rolling(14).mean()
    full_sma_200 = df['Close'].rolling(200).mean()

    mult_map = {"NQ":20,"ES":50,"YM":5,"RTY":50,"CL":1000,"GC":100}
    multiplier = next((v for k,v in mult_map.items() if k in sym_to_use), 1)
    is_avg_down = "Average Down" in saved_strategy

    ENTRY_VALUES  = [round(x, 2) for x in np.arange(0.12, 0.36, 0.01)]
    EXIT_VALUES   = [round(x, 2) for x in np.arange(0.70, 0.96, 0.01)]
    
    years_to_test = [2021, 2022, 2023, 2024, 2025]
    best_per_year = []

    print(f"\nRunning Yearly IBS Optimization for {sym_to_use}...")
    print(f"Mode: {saved_strategy} | Trend Filter: {saved_trend} | Max Hold: {saved_max_hold}d | Max Contracts: {saved_max_cont}\n")

    for year in years_to_test:
        # Slice for the year
        year_df = df[df.index.year == year]
        if year_df.empty:
            print(f"No data for {year}. Skipping.")
            continue
            
        year_atr = full_atr[full_atr.index.year == year]
        year_sma = full_sma_200[full_sma_200.index.year == year]
        
        results = []
        for entry, exit_ in product(ENTRY_VALUES, EXIT_VALUES):
            if entry >= exit_:
                continue
            r = run_backtest(year_df, entry, exit_, is_avg_down,
                             saved_trend, saved_max_hold, saved_max_cont,
                             multiplier, year_atr, year_sma)
            if r:
                r["entry"] = entry
                r["exit"]  = exit_
                results.append(r)
                
        if results:
            results_df = pd.DataFrame(results).sort_values("total_pts", ascending=False)
            best = results_df.iloc[0]
            best_per_year.append({
                "Year": year,
                "Best Entry": best["entry"],
                "Best Exit": best["exit"],
                "Trades": int(best["trades"]),
                "Win Rate %": round(best["win_rate"], 1),
                "Total Pts": round(best["total_pts"], 1),
                "Total USD": int(best["total_usd"])
            })

    if not best_per_year:
        print("No valid results found.")
        return

    final_df = pd.DataFrame(best_per_year)
    print("\n" + "="*80)
    print("  OPTIMAL IBS PARAMETERS BY YEAR (Based on Total Profit)")
    print("="*80)
    print(final_df.to_string(index=False))
    print("="*80)
    
    out_path = os.path.join(os.path.dirname(__file__), "..", "yearly_optimization_report.csv")
    final_df.to_csv(out_path, index=False)
    print(f"\nSaved to: yearly_optimization_report.csv")
    
    if os.name == 'nt':
        try: os.startfile(out_path)
        except: pass

if __name__ == "__main__":
    main()
