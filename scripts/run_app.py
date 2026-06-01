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
    futures_list = ["NQ", "ES", "YM", "RTY", "CL", "GC", "MNQ", "MES", "MYM", "M2K"]
    is_future = any(symbol.upper() == f for f in futures_list)

    if params.get("chart_data"):
        log("Using pre-loaded chart data from UI for backtest...")
        df = pd.DataFrame(params["chart_data"])
        try:
            def parse_time(t):
                if isinstance(t, (int, float)):
                    return datetime.fromtimestamp(t)
                return pd.to_datetime(t)
            df['Date'] = df['time'].apply(parse_time)
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
        except Exception as e:
            raise ValueError(f"chart_data parse error: {e} | cols={df.columns.tolist()} | row0={df.iloc[0].to_dict() if not df.empty else 'empty'}")

    elif csv_path and os.path.exists(csv_path):
        log(f"Loading futures data from CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        rename_map = {}
        for col in df.columns:
            lc = col.strip().lower()
            if lc in ['time', 'date', 'datetime', 'timestamp']: rename_map[col] = 'Date'
            elif lc == 'open': rename_map[col] = 'Open'
            elif lc == 'high': rename_map[col] = 'High'
            elif lc == 'low': rename_map[col] = 'Low'
            elif lc in ['close', 'last']: rename_map[col] = 'Close'
        df.rename(columns=rename_map, inplace=True)
        if 'Date' not in df.columns:
            raise ValueError("CSV must have a Date/Time column.")
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        log(f"Loaded {len(df)} rows from CSV ({start_date.date()} to {end_date.date()})")

    elif is_future:
        log(f"ERROR: '{symbol}' is a futures contract. Alpaca does not provide futures data.")
        log("Please provide a CSV file with historical data.")
        log("  - NinjaTrader, TradeStation, or Norgate Data can export NQ/ES CSVs.")
        log("  - Paste the full file path into the 'CSV Path' field in the Day Trading tab, then re-run.")
        return "\n".join(output), [], []

    else:
        # Stock: use Alpaca market data API (falls back to yfinance if key not set)
        tf_map_alpaca = {
            "1 min":  (1,  "Minute"),
            "5 mins": (5,  "Minute"),
            "15 mins":(15, "Minute"),
            "30 mins":(30, "Minute"),
            "1 hour": (1,  "Hour"),
            "4 hours":(4,  "Hour"),
            "1 day":  (1,  "Day"),
        }
        raw_tf = params.get("timeframe", params.get("sleep_time", "1 day"))
        alpaca_tf = tf_map_alpaca.get(raw_tf, (1, "Day"))

        import dotenv as _dotenv
        _dotenv.load_dotenv(override=True)
        alpaca_key    = os.getenv("ALPACA_API_KEY", "")
        alpaca_secret = os.getenv("ALPACA_API_SECRET", "")

        if alpaca_key and alpaca_secret:
            log(f"Downloading {symbol} ({raw_tf}) from Alpaca ({start_date.date()} to {end_date.date()})...")
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockBarsRequest
                from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
                unit_map = {"Minute": TimeFrameUnit.Minute, "Hour": TimeFrameUnit.Hour, "Day": TimeFrameUnit.Day}
                tf_obj = TimeFrame(alpaca_tf[0], unit_map[alpaca_tf[1]])
                client = StockHistoricalDataClient(alpaca_key, alpaca_secret)
                req = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=tf_obj,
                    start=start_date,
                    end=end_date + timedelta(days=1)
                )
                raw = client.get_stock_bars(req).df
                if raw is None or raw.empty:
                    log(f"Error: No data from Alpaca for '{symbol}'. Check ticker symbol.")
                    return "\n".join(output), [], []
                # Flatten multi-index (symbol, timestamp) -> just timestamp
                raw = raw.reset_index()
                raw = raw.rename(columns={"timestamp": "Date", "open": "Open", "high": "High",
                                           "low": "Low", "close": "Close"})
                raw["Date"] = pd.to_datetime(raw["Date"]).dt.tz_localize(None)
                df = raw.set_index("Date")[["Open", "High", "Low", "Close"]].copy()
                df.sort_index(inplace=True)
                log(f"Downloaded {len(df)} bars from Alpaca.")
            except Exception as e:
                log(f"Alpaca error: {e} -- falling back to Yahoo Finance.")
                alpaca_key = ""  # trigger fallback below

        if not alpaca_key or not alpaca_secret:
            # Fallback: yfinance
            tf_map_yf = {
                "1 min": "1m", "5 mins": "5m", "15 mins": "15m",
                "30 mins": "30m", "1 hour": "60m", "4 hours": "60m", "1 day": "1d"
            }
            yf_interval = tf_map_yf.get(raw_tf, "1d")
            days_back = (end_date - start_date).days
            if yf_interval in ["1m", "5m", "15m", "30m"] and days_back > 59:
                log(f"Note: yfinance intraday limited to 60 days. Adjusting start date.")
                start_date = end_date - timedelta(days=59)
            log(f"Downloading {symbol} ({yf_interval}) from Yahoo Finance ({start_date.date()} to {end_date.date()})...")
            try:
                import yfinance as yf
                raw = yf.download(symbol, start=start_date, end=end_date + timedelta(days=1),
                                  interval=yf_interval, progress=False, auto_adjust=True)
                if raw is None or raw.empty:
                    log(f"Error: No data from Yahoo Finance for '{symbol}'.")
                    return "\n".join(output), [], []
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                df = raw[['Open', 'High', 'Low', 'Close']].copy()
                df.index.name = 'Date'
                df.index = pd.to_datetime(df.index).tz_localize(None)
                df.sort_index(inplace=True)
                log(f"Downloaded {len(df)} bars from Yahoo Finance.")
            except Exception as e:
                log(f"Yahoo Finance error: {e}")
                return "\n".join(output), [], []

    # Drop missing
    df = df.dropna()

    # --- Timeframe Resampling ---
    # Map UI timeframe labels to pandas offset aliases
    tf_resample_map = {
        "1 min":   "1min",
        "5 mins":  "5min",
        "15 mins": "15min",
        "30 mins": "30min",
        "1 hour":  "1h",
        "4 hours": "4h",
        "1 day":   "1D",
    }
    requested_tf = params.get("timeframe", params.get("sleep_time", ""))
    resample_rule = tf_resample_map.get(requested_tf, "")

    if resample_rule and resample_rule != "1min":
        # Only resample if a timeframe is chosen and it's not already 1-min
        pre_len = len(df)
        ohlc_dict = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        df = df[["Open", "High", "Low", "Close"]].resample(resample_rule).agg(ohlc_dict).dropna()
        log(f"Resampled {pre_len} x 1-min bars -> {len(df)} x {requested_tf} bars.")
    else:
        log(f"Using data as-is ({len(df)} bars, timeframe: {requested_tf or 'auto'}).")

    df['High'] = pd.to_numeric(df['High'])
    df['Low'] = pd.to_numeric(df['Low'])
    df['Close'] = pd.to_numeric(df['Close'])
    df['Open'] = pd.to_numeric(df['Open'])
    
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
    
    strategy_name = params.get("strategy", "IBS Strategy (Average Down)")
    if "Silver Bullet" in strategy_name:
        return run_sb_backtest(df, params, log, output)

    if "Blended" in strategy_name:
        return run_blended_backtest(df, params, log, output)
        
    # Determine multiplier
    raw_ticker = params["symbol"].upper()
    multiplier = 1
    contract_type = "Shares"
    if raw_ticker == "MNQ":
        multiplier = 2
        contract_type = "MNQ Contracts ($2/pt)"
    elif raw_ticker == "MES":
        multiplier = 5
        contract_type = "MES Contracts ($5/pt)"
    elif raw_ticker == "MYM":
        multiplier = 0.5
        contract_type = "MYM Contracts ($0.5/pt)"
    elif raw_ticker == "M2K":
        multiplier = 5
        contract_type = "M2K Contracts ($5/pt)"
    elif raw_ticker == "MCL":
        multiplier = 100
        contract_type = "MCL Contracts ($100/pt)"
    elif raw_ticker == "MGC":
        multiplier = 10
        contract_type = "MGC Contracts ($10/pt)"
    elif "NQ" in raw_ticker: 
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
                    "Reason": "",
                    "IBS": round(current_ibs, 4)
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
                    "Reason": reason,
                    "IBS": round(current_ibs, 4)
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
                    "Reason": "Time Limit",
                    "IBS": round(current_ibs, 4)
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
                    "Reason": "IBS Exit",
                    "IBS": round(current_ibs, 4)
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] IBS Exit: SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue

    if not trades:
        log("No trades executed based on criteria.")
        return "\n".join(output), [], []
        
    import numpy as np
    
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["Dollars"] > 0]
    losing_trades = [t for t in trades if t["Dollars"] <= 0]
    
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = sum(t["Dollars"] for t in winning_trades)
    gross_loss = abs(sum(t["Dollars"] for t in losing_trades))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.99 if gross_profit > 0 else 0.0)
    
    avg_win = (gross_profit / num_wins) if num_wins > 0 else 0.0
    avg_loss = (gross_loss / num_losses) if num_losses > 0 else 0.0
    
    total_dollars = sum(t["Dollars"] for t in trades)
    avg_trade_pl = total_dollars / total_trades if total_trades > 0 else 0.0
    
    trade_profits = [t["Dollars"] for t in trades]
    if len(trade_profits) > 1 and np.std(trade_profits) > 0:
        sharpe_ratio = np.mean(trade_profits) / np.std(trade_profits)
    else:
        sharpe_ratio = 0.0
        
    expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
    
    total_return_pct = sum(t["Profit %"] for t in trades)
    total_points = sum(t["Points"] for t in trades)
    
    max_consec_loss = 0
    current_consec = 0
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
            
        if t["Dollars"] < 0:
            current_consec += 1
            if current_consec > max_consec_loss:
                max_consec_loss = current_consec
        else:
            current_consec = 0
    
    log(f"\n--- Final Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ---")
    log(f"Total Trades: {total_trades}")
    log(f"Win Rate: {win_rate:.2f}%")
    log(f"Total Dollar Return (1 {raw_ticker} Contract): {total_points:+.2f}")
    log(f"Max Drawdown: -{max_dd / multiplier:.2f}")
    log(f"Total Points Captured: {total_points:+.2f} pts")
    log(f"Cumulative Return (Uncompounded %): {total_return_pct:+.2f}%")
    log(f"Average Trade P/L: {avg_trade_pl / multiplier:.2f}")
    log(f"Profit Factor: {profit_factor:.2f}")
    log(f"Sharpe Ratio (Trade): {sharpe_ratio:.2f}")
    log(f"Expectancy: {expectancy / multiplier:.2f}")
    log(f"Max Consecutive Losses: {max_consec_loss}")
    log(f"Average Win: {avg_win / multiplier:.2f}")
    log(f"Average Loss: -{avg_loss / multiplier:.2f}")
    log("-------------------------------------------------")
    
    return "\n".join(output), trades, ledger

def run_blended_backtest(df, params, log, output):
    """
    Blended Strategy: Two independent IBS legs running in parallel.
      Leg A — Core:     Entry IBS < 0.32, Exit IBS > 0.90
      Leg B — Deep Dip: Entry IBS < 0.24, Exit IBS > 0.85

    Each leg is fully independent — its own contract stack and cost basis.
    Results are merged into a single trade ledger sorted chronologically.
    """
    raw_ticker = params["symbol"].upper()
    multiplier = 1
    contract_type = "Shares"
    if raw_ticker == "MNQ":
        multiplier = 2;  contract_type = "MNQ Contracts ($2/pt)"
    elif raw_ticker == "MES":
        multiplier = 5;  contract_type = "MES Contracts ($5/pt)"
    elif raw_ticker == "MYM":
        multiplier = 0.5; contract_type = "MYM Contracts ($0.5/pt)"
    elif raw_ticker == "M2K":
        multiplier = 5;  contract_type = "M2K Contracts ($5/pt)"
    elif raw_ticker == "MCL":
        multiplier = 100; contract_type = "MCL Contracts ($100/pt)"
    elif raw_ticker == "MGC":
        multiplier = 10; contract_type = "MGC Contracts ($10/pt)"
    elif "NQ" in raw_ticker:
        multiplier = 20; contract_type = "NQ Contracts ($20/pt)"
    elif "ES" in raw_ticker:
        multiplier = 50; contract_type = "ES Contracts ($50/pt)"
    elif "YM" in raw_ticker:
        multiplier = 5;  contract_type = "YM Contracts ($5/pt)"
    elif "RTY" in raw_ticker:
        multiplier = 50; contract_type = "RTY Contracts ($50/pt)"
    elif "CL" in raw_ticker:
        multiplier = 1000; contract_type = "CL Contracts ($1000/pt)"
    elif "GC" in raw_ticker:
        multiplier = 100; contract_type = "GC Contracts ($100/pt)"
    else:
        contract_type = "Shares (1:1 Ratio)"

    # Blend parameters — use user inputs, fall back to optimised defaults
    CORE_ENTRY     = params.get('entry_threshold',   0.32)
    CORE_EXIT      = params.get('exit_threshold',    0.90)
    DEEP_DIP_ENTRY = params.get('entry_threshold_b', 0.24)
    DEEP_DIP_EXIT  = params.get('exit_threshold_b',  0.85)
    if DEEP_DIP_ENTRY is None: DEEP_DIP_ENTRY = 0.24
    if DEEP_DIP_EXIT  is None: DEEP_DIP_EXIT  = 0.85

    start_date = df.index[0]
    end_date   = df.index[-1]

    log(f"\n--- IBS Blended Strategy | {contract_type} ---")
    log(f"    Leg A  [Core]     — Entry IBS < {CORE_ENTRY} | Exit IBS > {CORE_EXIT}")
    log(f"    Leg B  [Deep Dip] — Entry IBS < {DEEP_DIP_ENTRY} | Exit IBS > {DEEP_DIP_EXIT}")
    log(f"    Each leg is independent. Deep Dip only fires on more extreme pullbacks.")
    log("")

    ibs   = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    close = df['Close']

    # --- State for each leg ---
    leg_a_held = 0;  leg_a_cost = 0.0;  leg_a_days = 0
    leg_b_held = 0;  leg_b_cost = 0.0;  leg_b_days = 0

    raw_trades = []   # combined, will be sorted at end
    ledger     = []

    for i in range(len(df)):
        cur_date  = df.index[i]
        cur_close = close.iloc[i]
        cur_ibs   = ibs.iloc[i]
        if pd.isna(cur_ibs):
            continue

        if leg_a_held > 0: leg_a_days += 1
        if leg_b_held > 0: leg_b_days += 1

        # ---- Leg A: Core ----
        if cur_ibs < CORE_ENTRY:
            if leg_a_held == 0: leg_a_days = 1
            leg_a_held += 1
            leg_a_cost += cur_close
            log(f"[{cur_date.strftime('%Y-%m-%d')}] [Core]     BUY 1 @ {cur_close:.2f} | Held: {leg_a_held} | IBS: {cur_ibs:.4f}")
            ledger.append({"Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Core",
                           "Action": "BUY", "Contracts": 1, "Price": round(cur_close, 2),
                           "Total Held": leg_a_held, "Avg Entry": "", "P/L Pts": "", "P/L USD": "",
                           "Reason": "Core Entry", "IBS": round(cur_ibs, 4)})
        elif leg_a_held > 0 and cur_ibs > CORE_EXIT:
            avg_a  = leg_a_cost / leg_a_held
            pts_a  = (cur_close * leg_a_held) - leg_a_cost
            usd_a  = pts_a * multiplier
            pct_a  = ((cur_close - avg_a) / avg_a) * 100
            log(f"[{cur_date.strftime('%Y-%m-%d')}] [Core]     EXIT {leg_a_held} @ {cur_close:.2f} | Avg: {avg_a:.2f} | P/L: {pts_a:+.2f} pts (${usd_a:+.2f})")
            raw_trades.append({"Exit Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Core",
                               "Reason": "IBS Exit", "Contracts": leg_a_held,
                               "Avg Entry": round(avg_a, 2), "Exit Price": round(cur_close, 2),
                               "Profit %": round(pct_a, 2), "Points": round(pts_a, 2),
                               "Dollars": round(usd_a, 2)})
            ledger.append({"Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Core",
                           "Action": "SELL ALL", "Contracts": leg_a_held, "Price": round(cur_close, 2),
                           "Total Held": 0, "Avg Entry": round(avg_a, 2),
                           "P/L Pts": round(pts_a, 2), "P/L USD": round(usd_a, 2),
                           "Reason": "Core IBS Exit", "IBS": round(cur_ibs, 4)})
            leg_a_held = 0; leg_a_cost = 0.0; leg_a_days = 0

        # ---- Leg B: Deep Dip ----
        if cur_ibs < DEEP_DIP_ENTRY:
            if leg_b_held == 0: leg_b_days = 1
            leg_b_held += 1
            leg_b_cost += cur_close
            log(f"[{cur_date.strftime('%Y-%m-%d')}] [DeepDip]  BUY 1 @ {cur_close:.2f} | Held: {leg_b_held} | IBS: {cur_ibs:.4f}")
            ledger.append({"Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Deep Dip",
                           "Action": "BUY", "Contracts": 1, "Price": round(cur_close, 2),
                           "Total Held": leg_b_held, "Avg Entry": "", "P/L Pts": "", "P/L USD": "",
                           "Reason": "Deep Dip Entry", "IBS": round(cur_ibs, 4)})
        elif leg_b_held > 0 and cur_ibs > DEEP_DIP_EXIT:
            avg_b  = leg_b_cost / leg_b_held
            pts_b  = (cur_close * leg_b_held) - leg_b_cost
            usd_b  = pts_b * multiplier
            pct_b  = ((cur_close - avg_b) / avg_b) * 100
            log(f"[{cur_date.strftime('%Y-%m-%d')}] [DeepDip]  EXIT {leg_b_held} @ {cur_close:.2f} | Avg: {avg_b:.2f} | P/L: {pts_b:+.2f} pts (${usd_b:+.2f})")
            raw_trades.append({"Exit Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Deep Dip",
                               "Reason": "IBS Exit", "Contracts": leg_b_held,
                               "Avg Entry": round(avg_b, 2), "Exit Price": round(cur_close, 2),
                               "Profit %": round(pct_b, 2), "Points": round(pts_b, 2),
                               "Dollars": round(usd_b, 2)})
            ledger.append({"Date": cur_date.strftime('%Y-%m-%d'), "Leg": "Deep Dip",
                           "Action": "SELL ALL", "Contracts": leg_b_held, "Price": round(cur_close, 2),
                           "Total Held": 0, "Avg Entry": round(avg_b, 2),
                           "P/L Pts": round(pts_b, 2), "P/L USD": round(usd_b, 2),
                           "Reason": "Deep Dip IBS Exit", "IBS": round(cur_ibs, 4)})
            leg_b_held = 0; leg_b_cost = 0.0; leg_b_days = 0

    # Sort combined ledger by date
    ledger.sort(key=lambda x: x["Date"])
    raw_trades.sort(key=lambda x: x["Exit Date"])
    trades = raw_trades

    if not trades:
        log("No trades executed based on criteria.")
        return "\n".join(output), [], []

    import numpy as np

    total_trades    = len(trades)
    winning_trades  = [t for t in trades if t["Dollars"] > 0]
    losing_trades   = [t for t in trades if t["Dollars"] <= 0]
    num_wins        = len(winning_trades)
    num_losses      = len(losing_trades)
    win_rate        = (num_wins / total_trades) * 100
    gross_profit    = sum(t["Dollars"] for t in winning_trades)
    gross_loss      = abs(sum(t["Dollars"] for t in losing_trades))
    profit_factor   = (gross_profit / gross_loss) if gross_loss > 0 else 99.99
    avg_win         = (gross_profit / num_wins) if num_wins > 0 else 0.0
    avg_loss        = (gross_loss / num_losses) if num_losses > 0 else 0.0
    total_dollars   = sum(t["Dollars"] for t in trades)
    total_points    = sum(t["Points"] for t in trades)
    avg_trade_pl    = total_dollars / total_trades
    trade_profits   = [t["Dollars"] for t in trades]
    sharpe_ratio    = (np.mean(trade_profits) / np.std(trade_profits)) if np.std(trade_profits) > 0 else 0.0
    expectancy      = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
    total_return_pct= sum(t["Profit %"] for t in trades)

    # Core vs Deep Dip split
    core_trades = [t for t in trades if t["Leg"] == "Core"]
    dd_trades   = [t for t in trades if t["Leg"] == "Deep Dip"]

    equity = 0; peak_equity = 0; max_dd = 0; max_consec_loss = 0; current_consec = 0
    for t in trades:
        equity += t["Dollars"]
        if equity > peak_equity: peak_equity = equity
        dd = peak_equity - equity
        if dd > max_dd: max_dd = dd
        if t["Dollars"] < 0:
            current_consec += 1
            if current_consec > max_consec_loss: max_consec_loss = current_consec
        else:
            current_consec = 0

    log(f"\n--- Blended Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ---")
    log(f"Strategy:         Blended Core (0.32/0.90) + Deep Dip (0.24/0.85)")
    log(f"Total Trades:     {total_trades}  (Core: {len(core_trades)} | Deep Dip: {len(dd_trades)})")
    log(f"Win Rate:         {win_rate:.2f}%")
    log(f"Total Points:     {total_points:+.2f} pts")
    log(f"Max Drawdown:     -{max_dd / multiplier:.2f}")
    log(f"Avg Trade P/L:    {avg_trade_pl / multiplier:.2f}")
    log(f"Profit Factor:    {profit_factor:.2f}")
    log(f"Sharpe Ratio:     {sharpe_ratio:.2f}")
    log(f"Expectancy:       {expectancy / multiplier:.2f}")
    log(f"Max Consec Loss:  {max_consec_loss}")
    log(f"Avg Win:          {avg_win / multiplier:.2f}")
    log(f"Avg Loss:         -{avg_loss / multiplier:.2f}")
    log("-------------------------------------------------")

    return "\n".join(output), trades, ledger


def run_sb_backtest(df, params, log, output):

    start_date = df.index[0]
    end_date = df.index[-1]
    raw_ticker = params["symbol"].upper()
    multiplier = 1
    contract_type = "Shares"
    if raw_ticker == "MNQ":
        multiplier = 2
        contract_type = "MNQ Contracts ($2/pt)"
    elif raw_ticker == "MES":
        multiplier = 5
        contract_type = "MES Contracts ($5/pt)"
    elif raw_ticker == "MYM":
        multiplier = 0.5
        contract_type = "MYM Contracts ($0.5/pt)"
    elif raw_ticker == "M2K":
        multiplier = 5
        contract_type = "M2K Contracts ($5/pt)"
    elif raw_ticker == "MCL":
        multiplier = 100
        contract_type = "MCL Contracts ($100/pt)"
    elif raw_ticker == "MGC":
        multiplier = 10
        contract_type = "MGC Contracts ($10/pt)"
    elif "NQ" in raw_ticker: 
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
    
    trades = []
    ledger = []
    contracts_held = 0
    total_cost = 0
    
    rr_ratio = 2.0
    active_fvg = None
    fvg_entry = 0.0
    fvg_sl = 0.0
    fvg_tp = 0.0
    
    log(f"\n--- Executed Trades ({contract_type}) | Mode: ICT Silver Bullet ---")
    
    for i in range(4, len(df)):
        current_date = df.index[i]
        c_open, c_high, c_low, c_close = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        
        current_ibs = (c_close - c_low) / (c_high - c_low) if c_high > c_low else 0.5
        
        # Check Silver Bullet Window (10-11 AM EST)
        hour = current_date.hour
        is_sb_window = (hour == 10)
        
        if not is_sb_window and contracts_held == 0:
            active_fvg = None # Reset pending outside window
            
        if contracts_held != 0:
            # Manage Open Position
            if active_fvg == 'bullish':
                if c_low <= fvg_sl:
                    loss = fvg_entry - fvg_sl
                    log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] SELL (Stop Loss) 1 Contract @ {fvg_sl:.2f} | P/L: {-loss:+.2f} pts")
                    contracts_held = 0
                    ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "SELL (SL)", "Contracts": 0, "Price": round(fvg_sl, 2), "Total Held": 0, "Avg Entry": round(fvg_entry, 2), "P/L Pts": round(-loss, 2), "P/L USD": round(-loss*multiplier, 2), "Reason": "SL Hit", "IBS": round(current_ibs, 4)})
                    trades.append({"Profit %": (-loss/fvg_entry)*100, "Points": -loss, "Dollars": -loss*multiplier})
                    active_fvg = None
                elif c_high >= fvg_tp:
                    profit = fvg_tp - fvg_entry
                    log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] SELL (Take Profit) 1 Contract @ {fvg_tp:.2f} | P/L: {profit:+.2f} pts")
                    contracts_held = 0
                    ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "SELL (TP)", "Contracts": 0, "Price": round(fvg_tp, 2), "Total Held": 0, "Avg Entry": round(fvg_entry, 2), "P/L Pts": round(profit, 2), "P/L USD": round(profit*multiplier, 2), "Reason": "TP Hit", "IBS": round(current_ibs, 4)})
                    trades.append({"Profit %": (profit/fvg_entry)*100, "Points": profit, "Dollars": profit*multiplier})
                    active_fvg = None
            elif active_fvg == 'bearish':
                if c_high >= fvg_sl:
                    loss = fvg_sl - fvg_entry
                    log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] BUY TO COVER (Stop Loss) 1 Contract @ {fvg_sl:.2f} | P/L: {-loss:+.2f} pts")
                    contracts_held = 0
                    ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "BUY COVER (SL)", "Contracts": 0, "Price": round(fvg_sl, 2), "Total Held": 0, "Avg Entry": round(fvg_entry, 2), "P/L Pts": round(-loss, 2), "P/L USD": round(-loss*multiplier, 2), "Reason": "SL Hit", "IBS": round(current_ibs, 4)})
                    trades.append({"Profit %": (-loss/fvg_entry)*100, "Points": -loss, "Dollars": -loss*multiplier})
                    active_fvg = None
                elif c_low <= fvg_tp:
                    profit = fvg_entry - fvg_tp
                    log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] BUY TO COVER (Take Profit) 1 Contract @ {fvg_tp:.2f} | P/L: {profit:+.2f} pts")
                    contracts_held = 0
                    ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "BUY COVER (TP)", "Contracts": 0, "Price": round(fvg_tp, 2), "Total Held": 0, "Avg Entry": round(fvg_entry, 2), "P/L Pts": round(profit, 2), "P/L USD": round(profit*multiplier, 2), "Reason": "TP Hit", "IBS": round(current_ibs, 4)})
                    trades.append({"Profit %": (profit/fvg_entry)*100, "Points": profit, "Dollars": profit*multiplier})
                    active_fvg = None
            continue
            
        if is_sb_window and contracts_held == 0:
            c1_h, c1_l = df['High'].iloc[i-3], df['Low'].iloc[i-3]
            c3_h, c3_l = df['High'].iloc[i-1], df['Low'].iloc[i-1]
            
            if c1_h < c3_l and active_fvg is None:
                active_fvg = 'bullish_pending'
                fvg_entry = c3_l
                fvg_sl = c1_l
                fvg_tp = fvg_entry + ((fvg_entry - fvg_sl) * rr_ratio)
            elif c1_l > c3_h and active_fvg is None:
                active_fvg = 'bearish_pending'
                fvg_entry = c3_h
                fvg_sl = c1_h
                fvg_tp = fvg_entry - ((fvg_sl - fvg_entry) * rr_ratio)
                
            if active_fvg == 'bullish_pending' and c_low <= fvg_entry:
                contracts_held = 1
                active_fvg = 'bullish'
                log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] BUY 1 Contract @ {fvg_entry:.2f}")
                ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "BUY", "Contracts": 1, "Price": round(fvg_entry, 2), "Total Held": 1, "Avg Entry": "", "P/L Pts": "", "P/L USD": "", "Reason": "", "IBS": round(current_ibs, 4)})
            elif active_fvg == 'bearish_pending' and c_high >= fvg_entry:
                contracts_held = -1
                active_fvg = 'bearish'
                log(f"[{current_date.strftime('%Y-%m-%d %H:%M')}] SELL SHORT 1 Contract @ {fvg_entry:.2f}")
                ledger.append({"Date": current_date.strftime('%Y-%m-%d %H:%M'), "Action": "SELL SHORT", "Contracts": -1, "Price": round(fvg_entry, 2), "Total Held": -1, "Avg Entry": "", "P/L Pts": "", "P/L USD": "", "Reason": "", "IBS": round(current_ibs, 4)})

    if not trades:
        log("No trades executed based on criteria.")
        return "\n".join(output), [], []
        
    import numpy as np
    
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["Dollars"] > 0]
    losing_trades = [t for t in trades if t["Dollars"] <= 0]
    
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0
    
    gross_profit = sum(t["Dollars"] for t in winning_trades)
    gross_loss = abs(sum(t["Dollars"] for t in losing_trades))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.99 if gross_profit > 0 else 0.0)
    
    avg_win = (gross_profit / num_wins) if num_wins > 0 else 0.0
    avg_loss = (gross_loss / num_losses) if num_losses > 0 else 0.0
    
    total_dollars = sum(t["Dollars"] for t in trades)
    avg_trade_pl = total_dollars / total_trades if total_trades > 0 else 0.0
    
    trade_profits = [t["Dollars"] for t in trades]
    if len(trade_profits) > 1 and np.std(trade_profits) > 0:
        sharpe_ratio = np.mean(trade_profits) / np.std(trade_profits)
    else:
        sharpe_ratio = 0.0
        
    expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
    
    total_return_pct = sum(t["Profit %"] for t in trades)
    total_points = sum(t["Points"] for t in trades)
    
    max_consec_loss = 0
    current_consec = 0
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
            
        if t["Dollars"] < 0:
            current_consec += 1
            if current_consec > max_consec_loss:
                max_consec_loss = current_consec
        else:
            current_consec = 0
    
    log(f"\n--- Final Results ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) ---")
    log(f"Total Trades: {total_trades}")
    log(f"Win Rate: {win_rate:.2f}%")
    log(f"Total Dollar Return (1 {raw_ticker} Contract): {total_points:+.2f}")
    log(f"Max Drawdown: -{max_dd / multiplier:.2f}")
    log(f"Total Points Captured: {total_points:+.2f} pts")
    log(f"Cumulative Return (Uncompounded %): {total_return_pct:+.2f}%")
    log(f"Average Trade P/L: {avg_trade_pl / multiplier:.2f}")
    log(f"Profit Factor: {profit_factor:.2f}")
    log(f"Sharpe Ratio (Trade): {sharpe_ratio:.2f}")
    log(f"Expectancy: {expectancy / multiplier:.2f}")
    log(f"Max Consecutive Losses: {max_consec_loss}")
    log(f"Average Win: {avg_win / multiplier:.2f}")
    log(f"Average Loss: -{avg_loss / multiplier:.2f}")
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
            
            report_path = os.path.join("results", "backtest_report.txt")
            csv_path = os.path.join("results", f"backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
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
