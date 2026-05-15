import os
import sys
import json
from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime
import subprocess
import tkinter as tk
from tkinter import filedialog
import glob

# Add root directory to python path so imports work
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, ROOT_DIR)

from scripts.run_app import run_pandas_backtest
from src.ui.launcher import STATE_FILE

app = Flask(__name__)

# Global state for live price streaming
live_ticker = "NQ"
live_price_data = {"price": 0.0, "time": 0}

def market_data_worker():
    import asyncio
    import nest_asyncio
    import time
    nest_asyncio.apply()
    
    asyncio.set_event_loop(asyncio.new_event_loop())
    from ib_insync import IB, ContFuture, util
    ib = IB()
    
    current_contract = None
    market_data = None
    
    while True:
        try:
            if not ib.isConnected():
                for port in [4002, 7497, 4001, 7496]:
                    try:
                        ib.connect('127.0.0.1', port, clientId=101)
                        break
                    except:
                        pass
                        
            if ib.isConnected():
                global live_ticker, live_price_data
                
                # Check if we need to switch tickers
                live_ticker_upper = live_ticker.upper()
                if current_contract is None or current_contract.symbol != live_ticker_upper:
                    if market_data:
                        ib.cancelMktData(market_data.contract)
                        
                    future_tickers = ["NQ", "ES", "RTY", "YM", "GC", "CL", "MES", "MNQ", "M2K", "MYM", "ZB", "ZN", "ZF", "ZT"]
                    if live_ticker_upper in future_tickers:
                        exchange = "CME"
                        if live_ticker_upper in ["GC", "CL"]: exchange = "NYMEX"
                        elif live_ticker_upper in ["YM", "MYM", "ZB", "ZN", "ZF", "ZT"]: exchange = "CBOT"
                        current_contract = ContFuture(live_ticker_upper, exchange)
                    else:
                        from ib_insync import Stock
                        current_contract = Stock(live_ticker_upper, 'SMART', 'USD')
                        
                    ib.qualifyContracts(current_contract)
                    market_data = ib.reqMktData(current_contract, "", False, False)
                
                if market_data and market_data.last == market_data.last: # Check for NaN
                    if market_data.last > 0:
                        live_price_data["price"] = market_data.last
                        # We use local time for the update tick to append quickly
                        live_price_data["time"] = int(time.time())
                        
                ib.sleep(1)
            else:
                import time
                time.sleep(2)
        except Exception as e:
            import time
            time.sleep(2)

import threading
threading.Thread(target=market_data_worker, daemon=True).start()

@app.route('/api/live_price', methods=['GET'])
def get_live_price():
    global live_ticker
    ticker = request.args.get('ticker')
    if ticker and ticker != live_ticker:
        live_ticker = ticker
    return jsonify({"status": "success", "data": live_price_data})
@app.route('/')
def index():
    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except:
            pass
    return render_template('index.html', state=state)

@app.route('/api/save_state', methods=['POST'])
def save_state():
    req = request.json
    try:
        state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
            except:
                pass
                
        # Handle both the old format (full dict) and new format (key/value)
        if "key" in req and "value" in req:
            state[req["key"]] = req["value"]
        else:
            state.update(req)
            
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/browse_csv', methods=['GET'])
def browse_csv():
    try:
        # Create a hidden tk window to show the dialog
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Historical CSV Data",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        root.destroy()
        return jsonify({"status": "success", "path": file_path})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/backtest', methods=['POST'])
def run_backtest_api():
    params = request.json
    try:
        # Make sure values are cast properly
        try: params['entry_threshold'] = float(params.get('entry_ibs', 0.21))
        except: params['entry_threshold'] = 0.21
        try: params['exit_threshold'] = float(params.get('exit_ibs', 0.87))
        except: params['exit_threshold'] = 0.87
        try: params['take_profit'] = float(params.get('take_profit', 0.0))
        except: params['take_profit'] = 0.0
        try: params['stop_loss'] = float(params.get('stop_loss', 0.0))
        except: params['stop_loss'] = 0.0
        try: params['max_hold_days'] = int(params.get('max_hold_days', 0))
        except: params['max_hold_days'] = 0
        try: params['max_contracts'] = int(params.get('max_contracts', 0))
        except: params['max_contracts'] = 0
        
        params['sleep_time'] = params.get('timeframe', '1 day')
        params['symbol'] = params.get('ticker', 'NQ')

        # Run backtest
        report_text, trades_list, ledger = run_pandas_backtest(params)
        
        # Save to CSV and Text
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(ROOT_DIR, f"backtest_report_{stamp}.txt")
        csv_path = os.path.join(ROOT_DIR, f"backtest_trades_{stamp}.csv")
        
        with open(report_path, "w") as f:
            f.write("Strategy Execution Report\n")
            f.write("=========================\n\n")
            f.write(report_text)
            
        if ledger:
            pd.DataFrame(ledger).to_csv(csv_path, index=False)
            
        # Parse metrics for DB
        import re
        tr_match = re.search(r'Total Trades:\s*(\d+)', report_text)
        wr_match = re.search(r'Win Rate:\s*([\d\.]+)%', report_text)
        dd_match = re.search(r'Max Drawdown:\s*-\$?([\d\.]+)', report_text)
        pnl_match = re.search(r'Total Dollar Return[^:]*:\s*\$?([\+\-\d\.]+)', report_text)
        
        tr = int(tr_match.group(1)) if tr_match else 0
        wr = float(wr_match.group(1)) if wr_match else 0.0
        dd = float(dd_match.group(1)) if dd_match else 0.0
        pnl = float(pnl_match.group(1).replace('+', '')) if pnl_match else 0.0
        
        from src.trading import db
        db.log_backtest_run(
            strategy=params.get('strategy', 'IBS Mean Reversion'),
            ticker=params['symbol'],
            timeframe=params['sleep_time'],
            total_trades=tr,
            win_rate=wr,
            total_profit=pnl,
            max_drawdown=dd
        )
            
        return jsonify({
            "status": "success", 
            "report": report_text, 
            "trades_file": csv_path, 
            "report_file": report_path,
            "data": ledger
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/optimize', methods=['POST'])
def run_optimize_api():
    script_path = os.path.join(ROOT_DIR, 'scripts', 'optimize_ibs.py')
    try:
        # Save state first
        with open(STATE_FILE, "w") as f:
            json.dump(request.json, f, indent=4)
            
        # Run subprocess and capture output
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        
        # Read the latest generated report to send back to the UI
        search_pattern = os.path.join(ROOT_DIR, "ibs_optimization_report_*.csv")
        files = glob.glob(search_pattern)
        data_json = []
        if files:
            latest_file = max(files, key=os.path.getmtime)
            df = pd.read_csv(latest_file)
            data_json = df.to_dict(orient='records')
            
        return jsonify({"status": "success", "output": result.stdout + "\n" + result.stderr, "data": data_json})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

live_process = None

@app.route('/api/live_results', methods=['GET'])
def get_live_results():
    file_path = os.path.join(ROOT_DIR, "live_trades.csv")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            return jsonify({"status": "success", "data": df.iloc[::-1].to_dict(orient='records')})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "success", "data": []})

@app.route('/api/db/trades', methods=['GET'])
def get_db_trades():
    try:
        from src.trading import db
        trades = db.get_all_live_trades()
        return jsonify({"status": "success", "data": trades})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/db/backtests', methods=['GET'])
def get_db_backtests():
    try:
        from src.trading import db
        runs = db.get_all_backtest_runs()
        return jsonify({"status": "success", "data": runs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/chart_data', methods=['POST'])
def get_chart_data():
    req = request.json
    ticker = req.get('ticker', 'NQ')
    timeframe = req.get('timeframe', '5 mins')
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
        
    # Connect to IBKR just to get data
    from ib_insync import IB, ContFuture
    import nest_asyncio
    nest_asyncio.apply()
    
    ib = IB()
    try:
        ports = [4002, 7497, 4001, 7496]
        connected = False
        for port in ports:
            try:
                ib.connect('127.0.0.1', port, clientId=99)
                connected = True
                break
            except:
                continue
                
        if not connected:
            return jsonify({"status": "error", "message": "Could not connect to IB Gateway"})
        
        ticker = ticker.upper()
        future_tickers = ["NQ", "ES", "RTY", "YM", "GC", "CL", "MES", "MNQ", "M2K", "MYM", "ZB", "ZN", "ZF", "ZT"]
        if ticker in future_tickers:
            exchange = "CME"
            if ticker in ["GC", "CL"]: exchange = "NYMEX"
            elif ticker in ["YM", "MYM", "ZB", "ZN", "ZF", "ZT"]: exchange = "CBOT"
            contract = ContFuture(ticker, exchange)
        else:
            from ib_insync import Stock
            contract = Stock(ticker, 'SMART', 'USD')
            
        try:
            ib.qualifyContracts(contract)
        except:
            pass
            
        if not contract.conId:
            ib.disconnect()
            return jsonify({"status": "error", "message": f"Invalid ticker or no data found: {ticker}"})
        
        duration_map = {
            "5 secs": "14400 S",
            "10 secs": "28800 S",
            "15 secs": "28800 S",
            "30 secs": "1 D",
            "1 min": "1 D",
            "5 mins": "2 D",
            "15 mins": "5 D",
            "1 hour": "10 D"
        }
        duration = duration_map.get(timeframe, "2 D")
        
        bars = ib.reqHistoricalData(
            contract, endDateTime='', durationStr=duration,
            barSizeSetting=timeframe, whatToShow='TRADES', useRTH=True
        )
        
        chart_data = []
        import datetime
        for bar in bars:
            if isinstance(bar.date, datetime.datetime):
                ts = int(bar.date.timestamp())
                # Lightweight charts requires UTC timestamp, we might need to offset it
                # but let's just use the timestamp directly.
            else:
                ts = bar.date.strftime('%Y-%m-%d')
                
            chart_data.append({
                "time": ts,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close
            })
            
        # Ensure data is sorted and unique
        seen = set()
        clean_data = []
        for d in sorted(chart_data, key=lambda x: x['time']):
            if d['time'] not in seen:
                seen.add(d['time'])
                clean_data.append(d)
                
        ib.disconnect()
        
        # Calculate Indicators using Pandas
        import pandas as pd
        import numpy as np
        if clean_data:
            df = pd.DataFrame(clean_data)
            
            # EMA 9 & 21
            df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
            
            # Stoch RSI (14, 3, 3)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            min_rsi = df['rsi'].rolling(14).min()
            max_rsi = df['rsi'].rolling(14).max()
            df['stoch_rsi'] = (df['rsi'] - min_rsi) / (max_rsi - min_rsi) * 100
            df['stoch_k'] = df['stoch_rsi'].rolling(3).mean()
            df['stoch_d'] = df['stoch_k'].rolling(3).mean()
            
            # TD Sequential (DeMark Setup)
            df['td_setup'] = 0
            df['td_dir'] = 0 # 1 for buy setup, -1 for sell setup
            setup_up = 0
            setup_down = 0
            
            for i in range(4, len(df)):
                if df['close'].iloc[i] > df['close'].iloc[i-4]:
                    setup_up += 1
                    setup_down = 0
                    if setup_up == 9:
                        df.at[i, 'td_setup'] = 9
                        df.at[i, 'td_dir'] = -1 # Sell signal
                        setup_up = 0
                elif df['close'].iloc[i] < df['close'].iloc[i-4]:
                    setup_down += 1
                    setup_up = 0
                    if setup_down == 9:
                        df.at[i, 'td_setup'] = 9
                        df.at[i, 'td_dir'] = 1 # Buy signal
                        setup_down = 0
                else:
                    setup_up = 0
                    setup_down = 0
                    
            # Fill NaN
            if hasattr(df, 'bfill'):
                df.bfill(inplace=True)
            else:
                df.fillna(method='bfill', inplace=True)
            df.fillna(0, inplace=True)
            
            clean_data = df.to_dict('records')

        return jsonify({"status": "success", "data": clean_data})
    except Exception as e:
        if ib.isConnected(): ib.disconnect()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/live_logs', methods=['GET'])
def get_live_logs():
    log_path = os.path.join(ROOT_DIR, "live_log.txt")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
                return jsonify({"status": "success", "logs": "".join(lines[-50:])})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "success", "logs": ""})

@app.route('/api/live', methods=['POST'])
def run_live_api():
    global live_process
    script_path = os.path.join(ROOT_DIR, 'src', 'trading', 'live_trader.py')
    try:
        if live_process and live_process.poll() is None:
            return jsonify({"status": "error", "message": "Live Trader is already running."})

        with open(STATE_FILE, "w") as f:
            json.dump(request.json, f, indent=4)
            
        flags = 0
        if sys.platform == 'win32':
            flags = subprocess.CREATE_NO_WINDOW
            
        live_process = subprocess.Popen([sys.executable, script_path], 
                                        creationflags=flags)
        
        return jsonify({"status": "success", "message": "Live Trader Started in Background."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/stop_live', methods=['POST'])
def stop_live_api():
    global live_process
    if live_process:
        try:
            live_process.terminate()
            live_process = None
            return jsonify({"status": "success", "message": "Live Trader Stopped."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error", "message": "No Live Trader running."})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
