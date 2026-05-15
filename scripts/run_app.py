import sys
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Ensure src/ is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_pandas_backtest(params):
    output = []
    def log(msg):
        print(msg)
        output.append(msg)
        
    symbol = params["symbol"]
    start_date_str = params["start_date"]
    end_date_str = params["end_date"]
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    except Exception as e:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3)

    csv_path = params.get("csv_path", "")
    futures_list = ["NQ", "ES", "YM", "RTY", "CL", "GC", "NQ=F", "ES=F"]
    is_future = any(symbol.upper().startswith(f) for f in futures_list)
    
    if csv_path and os.path.exists(csv_path):
        log(f"Loading custom data from CSV:\n{csv_path}")
        df = pd.read_csv(csv_path)
        rename_map = {}
        for col in df.columns:
            lower_col = col.strip().lower()
            if lower_col in ['time', 'date']: rename_map[col] = 'Date'
            elif lower_col == 'open': rename_map[col] = 'Open'
            elif lower_col == 'high': rename_map[col] = 'High'
            elif lower_col == 'low': rename_map[col] = 'Low'
            elif lower_col == 'close': rename_map[col] = 'Close'
        df.rename(columns=rename_map, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        df = df[(df.index >= start_date) & (df.index <= end_date)]
    else:
        log(f"Attempting to download data for {symbol} directly from Interactive Brokers (TWS)...")
        import nest_asyncio
        nest_asyncio.apply()
        from ib_insync import IB, ContFuture, Stock, util
        
        ib = IB()
        try:
            # Try connecting to TWS Paper/API (7497) or Live (7496)
            try:
                ib.connect('127.0.0.1', 7497, clientId=1)
            except:
                try:
                    ib.connect('127.0.0.1', 7496, clientId=1)
                except Exception:
                    log("IBKR Connection Error: Could not connect to TWS on port 7497 or 7496.")
                    log("Please ensure TWS is open, logged in, and 'Enable ActiveX and Socket Clients' is checked in Settings -> API -> Settings.")
                    return "\n".join(output), [], []
            
            ib_symbol = symbol.replace("=F", "")
            
            # Determine if it is a Stock or Future
            futures_list = ["NQ", "ES", "YM", "RTY", "CL", "GC", "BTC", "ETH"]
            is_future_contract = any(ib_symbol.upper() == f for f in futures_list)
            
            if is_future_contract:
                if ib_symbol == "YM":
                    contract = ContFuture('YM', 'CBOT')
                elif ib_symbol in ["GC", "CL"]:
                    contract = ContFuture(ib_symbol, 'NYMEX')
                elif ib_symbol in ["NQ", "ES", "RTY"]:
                    contract = ContFuture(ib_symbol, 'CME')
                else:
                    contract = ContFuture(ib_symbol, 'CME') # default fallback
            else:
                contract = Stock(ib_symbol, 'SMART', 'USD')
                
            ib.qualifyContracts(contract)
            
            days_to_now = (datetime.now() - start_date).days
            duration = f"{max(1, days_to_now)} D"
            
            log(f"Requesting '{duration}' of Historical Data from IBKR for {ib_symbol}...")
            
            raw_tf = params.get("sleep_time", "1 day")
            use_rth = params.get("use_rth", False)
            show_type = 'BID' if is_future_contract else 'TRADES'
            
            bars = ib.reqHistoricalData(
                contract, endDateTime='',
                durationStr=duration,
                barSizeSetting=raw_tf,
                whatToShow=show_type,
                useRTH=use_rth,
                formatDate=1
            )
            ib.disconnect()
            
            if not bars:
                log(f"Error: No data returned from IBKR for {ib_symbol}.")
                return "\n".join(output), [], []
                
            df = util.df(bars)
            df.rename(columns={"date": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.index = df.index.tz_localize(None)
            
            # Filter locally to obey the ContFuture API restriction
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
        except Exception as e:
            log(f"IBKR API Error: {e}")
            if ib.isConnected(): ib.disconnect()
            return "\n".join(output), [], []
            
    # Drop missing
    df = df.dropna()
    
    df['High'] = pd.to_numeric(df['High'])
    df['Low'] = pd.to_numeric(df['Low'])
    df['Close'] = pd.to_numeric(df['Close'])
    
    # ATR Calculation
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()
    sma_200 = df['Close'].rolling(window=200).mean()
    
    ibs = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    
    high = df['High']
    low = df['Low']
    close = df['Close']
        
    # Determine multiplier
    raw_ticker = params["symbol"].upper()
    multiplier = 1
    contract_type = "Shares"
    if "NQ" in raw_ticker: 
        multiplier = 20
        contract_type = "NQ Contracts ($20/pt)"
    elif "ES" in raw_ticker: 
        multiplier = 50
        contract_type = "ES Contracts ($50/pt)"
    elif "YM" in raw_ticker: 
        multiplier = 5
        contract_type = "YM Contracts ($5/pt)"
    elif "RTY" in raw_ticker: 
        multiplier = 50
        contract_type = "RTY Contracts ($50/pt)"
    elif "CL" in raw_ticker: 
        multiplier = 1000
        contract_type = "CL Contracts ($1000/pt)"
    elif "GC" in raw_ticker: 
        multiplier = 100
        contract_type = "GC Contracts ($100/pt)"
    else:
        contract_type = "Shares (1:1 Ratio)"
        
    entry_threshold = params["entry_threshold"]
    exit_threshold = params["exit_threshold"]
    
    contracts_held = 0
    total_cost = 0
    trades = []
    ledger = []
    
    strategy_name = params.get("strategy", "IBS Strategy (Average Down)")
    is_average_down = "Average Down" in strategy_name
    
    tp_val = params.get("take_profit", 0.0)
    sl_val = params.get("stop_loss", 0.0)
    risk_type = params.get("risk_type", "Percentage (%)")
    is_points = "Points" in risk_type
    
    trend_filter = params.get("trend_filter", False)
    max_hold_days = params.get("max_hold_days", 0)
    max_contracts = params.get("max_contracts", 0)
    
    highest_high_since_entry = 0.0
    days_held = 0
    
    log(f"\n--- Executed Trades ({contract_type}) | Mode: {'Average Down' if is_average_down else 'Single Entry'} ---")
    for i in range(len(df)):
        current_date = df.index[i]
        current_close = close.iloc[i]
        current_ibs = ibs.iloc[i]
        current_atr = atr.iloc[i] if not pd.isna(atr.iloc[i]) else 1.0
        
        if contracts_held > 0:
            days_held += 1
        
        if current_ibs < entry_threshold:
            if not is_average_down and contracts_held > 0:
                pass # Already in position, don't average down
            elif trend_filter and current_close < sma_200.iloc[i]:
                pass # Blocked by 200 SMA Trend Filter
            elif max_contracts > 0 and contracts_held >= max_contracts:
                pass # Max contracts cap reached
            else:
                if contracts_held == 0:
                    highest_high_since_entry = current_close
                    days_held = 1
                contracts_held += 1
                total_cost += current_close
                log(f"[{current_date.strftime('%Y-%m-%d')}] BUY 1 Contract @ {current_close:.2f} (Total Held: {contracts_held})")
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "BUY",
                    "Contracts": 1,
                    "Price": round(current_close, 2),
                    "Total Held": contracts_held,
                    "Avg Entry": "",
                    "P/L Pts": "",
                    "P/L USD": "",
                    "Reason": ""
                })
            
        elif contracts_held > 0:
            avg_entry_price = total_cost / contracts_held
            
            bar_high = high.iloc[i]
            bar_low = low.iloc[i]
            
            if bar_high > highest_high_since_entry:
                highest_high_since_entry = bar_high
                
            if risk_type == "Trailing ATR (Chandelier)":
                atr_dist = current_atr * sl_val if sl_val > 0 else 0
                tp_price = avg_entry_price + (current_atr * tp_val) if tp_val > 0 else 0
                sl_price = highest_high_since_entry - atr_dist if sl_val > 0 else 0
                
                hit_tp = tp_val > 0 and bar_high >= tp_price
                hit_sl = sl_val > 0 and bar_low <= sl_price
                
            elif risk_type == "ATR Stop":
                atr_dist = current_atr * sl_val if sl_val > 0 else 0
                tp_price = avg_entry_price + (current_atr * tp_val) if tp_val > 0 else 0
                sl_price = avg_entry_price - atr_dist if sl_val > 0 else 0
                
                hit_tp = tp_val > 0 and bar_high >= tp_price
                hit_sl = sl_val > 0 and bar_low <= sl_price
                
            elif is_points:
                tp_price = avg_entry_price + tp_val if tp_val > 0 else 0
                sl_price = avg_entry_price - sl_val if sl_val > 0 else 0
                
                hit_tp = tp_val > 0 and bar_high >= tp_price
                hit_sl = sl_val > 0 and bar_low <= sl_price
            else:
                tp_price = avg_entry_price * (1 + (tp_val/100.0))
                sl_price = avg_entry_price * (1 - (sl_val/100.0))
                
                max_profit_pct = ((bar_high - avg_entry_price) / avg_entry_price) * 100
                max_loss_pct = ((bar_low - avg_entry_price) / avg_entry_price) * 100
                
                hit_tp = tp_val > 0 and max_profit_pct >= tp_val
                hit_sl = sl_val > 0 and max_loss_pct <= -sl_val
            
            if hit_tp or hit_sl:
                if hit_sl and hit_tp:
                    reason = "SL Hit (Ambiguous intraday crossover)"
                    exit_price = sl_price
                elif hit_sl:
                    reason = "SL Hit"
                    exit_price = sl_price
                else:
                    reason = "TP Hit"
                    exit_price = tp_price
                    
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": reason,
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": reason
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] {reason}: SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue
                
            if max_hold_days > 0 and days_held > max_hold_days:
                exit_price = current_close
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "Time Limit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": "Time Limit"
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] Stale Trade (Time Limit): SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue
                
            if current_ibs > exit_threshold:
                exit_price = current_close
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "IBS Exit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": "IBS Exit"
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] IBS Exit: SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue

    if not trades:
        log("No trades executed based on criteria.")
        return "\n".join(output), [], []
        
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t["Profit %"] > 0])
    win_rate = (winning_trades / total_trades) * 100
    
    total_return_pct = sum(t["Profit %"] for t in trades)
    total_points = sum(t["Points"] for t in trades)
    total_dollars = sum(t["Dollars"] for t in trades)
    
    # Calculate Max Drawdown
    equity = 0
    peak_equity = 0
    max_dd = 0
    for t in trades:
        equity += t["Dollars"]
        if equity > peak_equity:
            peak_equity = equity
        dd = peak_equity - equity
        if dd > max_dd:
            max_dd = dd
    
    log(f"\n--- Final Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ---")
    log(f"Total Trades: {total_trades}")
    log(f"Win Rate: {win_rate:.2f}%")
    log(f"Max Drawdown: -${max_dd:.2f}")
    log(f"Total Points Captured: {total_points:+.2f} pts")
    log(f"Total Dollar Return (1 {raw_ticker} Contract): ${total_dollars:+.2f}")
    log(f"Cumulative Return (Uncompounded %): {total_return_pct:+.2f}%")
    log("-------------------------------------------------")
    
    return "\n".join(output), trades, ledger

def main():
    # 1. LAZY LOAD UI FIRST
    from src.ui.launcher import get_launch_parameters
    
    launch_params = get_launch_parameters()
    if not launch_params:
        print("Launcher was closed.")
        sys.exit(0)
        
    if launch_params["mode"] == "backtest":
        print("\nLoading Custom Backtest Engine (this may take a second)...")
        report_text, trades_list, ledger = run_pandas_backtest(launch_params)
        
        if report_text:
            import os
            import pandas as pd
            from datetime import datetime
            
            report_path = "backtest_report.txt"
            csv_path = f"backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(report_path, "w") as f:
                f.write("Strategy Execution Report\n")
                f.write("=========================\n\n")
                f.write(report_text)
                
            if trades_list:
                pd.DataFrame(ledger).to_csv(csv_path, index=False)
                
            print(f"\nReports saved locally. Opening automatically...")
            if os.name == 'nt':
                os.startfile(report_path)
                if trades_list:
                    os.startfile(csv_path)
            
            import sys
            sys.exit(0)
            
    elif launch_params["mode"] == "optimize":
        print("\nLoading Parameter Sweep Optimizer...")
        import subprocess
        import sys
        import os
        
        script_path = os.path.join(os.path.dirname(__file__), "optimize_ibs.py")
        subprocess.run([sys.executable, script_path])
        print("\nOptimization complete.")
        sys.exit(0)
            
    elif launch_params["mode"] == "live":
        print("\nLoading Live Trading Engine (Lumibot)...")
        from src.strategy.implementations.ibs_strategy import IBSStrategy
        from lumibot.brokers import InteractiveBrokers
        from lumibot.traders import Trader
        
        print("\n--- Starting Live Trading via Interactive Brokers (TWS) ---")
        print("Attempting to connect to TWS on 127.0.0.1:7497...")
        ibkr_config = {
            "clientId": 2, # Using 2 to avoid conflicting with backtest clientId 1
            "host": "127.0.0.1",
            "port": 7497, # Default TWS Paper Trading port
        }
        
        tf_map_lumibot = {
            "1 min": "1M",
            "5 mins": "5M",
            "15 mins": "15M",
            "30 mins": "30M",
            "1 hour": "1H",
            "4 hours": "4H",
            "1 day": "1D"
        }
        lumibot_tf = tf_map_lumibot.get(launch_params["sleep_time"], "1D")
        
        strategy_params = {
            "symbol": launch_params["symbol"].replace("=F", ""),
            "sleep_time": lumibot_tf,
            "entry_threshold": launch_params["entry_threshold"],
            "exit_threshold": launch_params["exit_threshold"],
            "is_average_down": "Average Down" in launch_params.get("strategy", "Average Down"),
            "take_profit": launch_params.get("take_profit", 0.0),
            "stop_loss": launch_params.get("stop_loss", 0.0),
"risk_type": launch_params.get("risk_type", "Percentage (%)"),
            "trend_filter": launch_params.get("trend_filter", False),
            "max_hold_days": launch_params.get("max_hold_days", 0),
            "max_contracts": launch_params.get("max_contracts", 0)
        }
        
        broker = InteractiveBrokers(ibkr_config)
        strategy = IBSStrategy(broker=broker, parameters=strategy_params)
        
        trader = Trader()
        trader.add_strategy(strategy)
        try:
            trader.run_all()
        except Exception as e:
            print(f"\nCRITICAL IBKR ERROR: {e}")
            print("Make sure TWS is fully running, logged in, and API Access is enabled on Port 7497 or 7496!")

if __name__ == "__main__":
    main()
