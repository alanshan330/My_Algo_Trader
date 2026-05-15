import sqlite3
import os
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(ROOT_DIR, "trading_database.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for live trades
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS live_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        strategy TEXT,
        ticker TEXT,
        action TEXT,
        quantity INTEGER,
        price REAL,
        ibs_value REAL
    )
    ''')
    
    # Table for backtest summaries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backtest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        strategy TEXT,
        ticker TEXT,
        timeframe TEXT,
        total_trades INTEGER,
        win_rate REAL,
        total_profit REAL,
        max_drawdown REAL
    )
    ''')
    
    conn.commit()
    conn.close()

def log_live_trade(strategy, ticker, action, quantity, price, ibs_value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO live_trades (timestamp, strategy, ticker, action, quantity, price, ibs_value)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), strategy, ticker, action, quantity, price, ibs_value))
    conn.commit()
    conn.close()

def log_backtest_run(strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO backtest_runs (timestamp, strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown))
    conn.commit()
    conn.close()

def get_all_live_trades():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM live_trades ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_backtest_runs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM backtest_runs ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Initialize on import
init_db()
