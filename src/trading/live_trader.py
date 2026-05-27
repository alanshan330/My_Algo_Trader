import sys
import os
import time
import json
from datetime import datetime
from ib_insync import IB, ContFuture, MarketOrder, util

# Add root to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, ROOT_DIR)

from src.trading import db

STATE_FILE = os.path.join(ROOT_DIR, "ui_state.json")
LIVE_TRADES_FILE = os.path.join(ROOT_DIR, "results", "live_trades.csv")
LOG_FILE = os.path.join(ROOT_DIR, "results", "live_log.txt")

def print_log(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")

def log_trade(action, qty, price, ticker, ibs, strategy="IBS Mean Reversion"):
    headers = ["Date", "Ticker", "Action", "Quantity", "Price", "IBS"]
    exists = os.path.exists(LIVE_TRADES_FILE)
    with open(LIVE_TRADES_FILE, "a") as f:
        if not exists:
            f.write(",".join(headers) + "\n")
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{ticker},{action},{qty},{price:.2f},{ibs:.4f}\n")
    
    # Also log to DB
    try:
        db.log_live_trade(strategy, ticker, action, qty, price, ibs)
    except Exception as e:
        print_log(f"DB Log Error: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def main():
    # Clear log file at startup
    with open(LOG_FILE, "w") as f:
        f.write(f"--- Live Log Started {datetime.now()} ---\n")

    print_log("="*50)
    print_log("  IBS AUTOMATED LIVE TRADER — INITIALIZING  ")
    print_log("="*50)
    
    state = load_state()
    ticker = state.get("ticker", "NQ")
    entry_ibs = float(state.get("entry_ibs", 0.23))
    exit_ibs = float(state.get("exit_ibs", 0.84))
    max_contracts = int(state.get("max_contracts", 0))
    is_avg_down = "Average Down" in state.get("strategy", "Average Down")
    timeframe = state.get("timeframe", "1 day")
    
    # Duration map based on timeframe (S=Seconds, D=Days, W=Weeks, M=Months, Y=Years)
    duration_map = {
        "1 min": "3600 S",
        "5 mins": "14400 S",
        "15 mins": "1 D",
        "1 hour": "1 D",
        "4 hours": "2 D",
        "1 day": "2 D"
    }
    duration = duration_map.get(timeframe, "2 D")
    
    # Sleep map based on timeframe (seconds)
    sleep_map = {
        "1 min": 60,
        "5 mins": 300,
        "15 mins": 900,
        "1 hour": 3600,
        "4 hours": 14400,
        "1 day": 21600 # Check every 6 hours for daily
    }
    sleep_time = sleep_map.get(timeframe, 300)
    
    ib = IB()
    
    # Try connecting to standard ports
    ports = [4002, 7497, 4001, 7496]
    connected = False
    for port in ports:
        try:
            print_log(f"Attempting to connect to IB Gateway on port {port}...")
            ib.connect('127.0.0.1', port, clientId=10)
            connected = True
            break
        except:
            continue
            
    if not connected:
        print_log("ERROR: Could not connect to IB Gateway or TWS.")
        print_log("Please ensure IB Gateway is running and API is enabled.")
        return

    print_log(f"SUCCESS: Connected to IBKR (Port: {port})")
    
    # Define Contract
    exchange = "CME"
    if ticker in ["GC", "CL"]: exchange = "NYMEX"
    elif ticker == "YM": exchange = "CBOT"
    
    contract = ContFuture(ticker, exchange)
    ib.qualifyContracts(contract)
    print_log(f"Target Contract: {contract.symbol} ({contract.exchange})")

    while True:
        try:
            print_log("Checking Market State...")
            
            # Fetch latest bars
            bars = ib.reqHistoricalData(
                contract, endDateTime='', durationStr=duration,
                barSizeSetting=timeframe, whatToShow='BID', useRTH=True
            )
            
            if not bars:
                print_log("Warning: No bar data received. Retrying in 60s...")
                time.sleep(60)
                continue
                
            last_bar = bars[-1]
            current_ibs = (last_bar.close - last_bar.low) / (last_bar.high - last_bar.low)
            
            print_log(f"Current Price: {last_bar.close:.2f} | Current IBS: {current_ibs:.4f}")
            
            # Check Position
            pos = [p for p in ib.positions() if p.contract.symbol == ticker]
            current_size = pos[0].position if pos else 0
            print_log(f"Current Position: {current_size} contracts")
            
            # Logic
            strategy_name = state.get("strategy", "IBS")
            if "Silver Bullet" in strategy_name:
                # Need last 4 bars for FVG
                if len(bars) >= 4:
                    c1 = bars[-4]
                    c3 = bars[-2]
                    c_low, c_high = last_bar.low, last_bar.high
                    
                    hour = datetime.now().hour
                    if hour == 10 and current_size == 0:
                        # Bullish FVG Setup
                        if c1.high < c3.low and c_low <= c3.low:
                            print_log(f"SILVER BULLET: Retraced into Bullish FVG! BUYING 1 CONTRACT.")
                            order = MarketOrder('BUY', 1)
                            trade = ib.placeOrder(contract, order)
                            print_log(f"Order Placed: {trade.orderStatus.status}")
                            log_trade("BUY", 1, last_bar.close, ticker, 0, strategy="ICT Silver Bullet")
                        # Bearish FVG Setup
                        elif c1.low > c3.high and c_high >= c3.high:
                            print_log(f"SILVER BULLET: Retraced into Bearish FVG! SELLING 1 CONTRACT.")
                            order = MarketOrder('SELL', 1)
                            trade = ib.placeOrder(contract, order)
                            print_log(f"Order Placed: {trade.orderStatus.status}")
                            log_trade("SELL SHORT", 1, last_bar.close, ticker, 0, strategy="ICT Silver Bullet")
            else:
                if current_ibs < entry_ibs:
                    if not is_avg_down and current_size > 0:
                        print_log("Entry signal triggered but 'Single Entry' mode active. Skipping.")
                    elif max_contracts > 0 and current_size >= max_contracts:
                        print_log(f"Entry signal triggered but Max Contracts ({max_contracts}) reached. Skipping.")
                    else:
                        print_log(f"SIGNAL: IBS ({current_ibs:.4f}) < {entry_ibs}. BUYING 1 CONTRACT.")
                        order = MarketOrder('BUY', 1)
                        trade = ib.placeOrder(contract, order)
                        print_log(f"Order Placed: {trade.orderStatus.status}")
                        log_trade("BUY", 1, last_bar.close, ticker, current_ibs)
                
                elif current_ibs > exit_ibs and current_size > 0:
                    print_log(f"SIGNAL: IBS ({current_ibs:.4f}) > {exit_ibs}. EXITING POSITION.")
                    order = MarketOrder('SELL', current_size)
                    trade = ib.placeOrder(contract, order)
                    print_log(f"Exit Order Placed: {trade.orderStatus.status}")
                    log_trade("SELL", current_size, last_bar.close, ticker, current_ibs)
                
                else:
                    print_log("No signal. Holding.")

            # Synchronize sleep with the bar boundary
            now_ts = time.time()
            wait_time = sleep_time - (now_ts % sleep_time) + 2 
            print_log(f"Next bar in {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            
        except Exception as e:
            print_log(f"Error during execution: {e}")
            time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFATAL CRASH: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to close this window...")
