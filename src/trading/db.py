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
        max_drawdown REAL,
        avg_trade_pl REAL,
        profit_factor REAL,
        sharpe_ratio REAL,
        expectancy REAL,
        max_consec_loss INTEGER,
        avg_win REAL,
        avg_loss REAL,
        entry_ibs REAL,
        exit_ibs REAL
    )
    ''')
    
    # Table for optimizer summaries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS optimizer_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        strategy TEXT,
        ticker TEXT,
        timeframe TEXT,
        best_params TEXT,
        best_profit REAL,
        best_win_rate REAL,
        best_drawdown REAL
    )
    ''')
    
    # Safely migrate existing tables
    try:
        cursor.execute("ALTER TABLE backtest_runs ADD COLUMN ledger_json TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Safely migrate advanced analytics columns if they don't exist
    new_cols = [
        ("avg_trade_pl", "REAL"), ("profit_factor", "REAL"), ("sharpe_ratio", "REAL"),
        ("expectancy", "REAL"), ("max_consec_loss", "INTEGER"), ("avg_win", "REAL"), ("avg_loss", "REAL"),
        ("entry_ibs", "REAL"), ("exit_ibs", "REAL")
    ]
    for col_name, col_type in new_cols:
        try:
            cursor.execute(f"ALTER TABLE backtest_runs ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass


    
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

def log_backtest_run(strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown, 
                     avg_trade_pl=0.0, profit_factor=0.0, sharpe_ratio=0.0, expectancy=0.0, max_consec_loss=0, avg_win=0.0, avg_loss=0.0, entry_ibs=0.0, exit_ibs=0.0, ledger_json="[]"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO backtest_runs (timestamp, strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown, avg_trade_pl, profit_factor, sharpe_ratio, expectancy, max_consec_loss, avg_win, avg_loss, entry_ibs, exit_ibs, ledger_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), strategy, ticker, timeframe, total_trades, win_rate, total_profit, max_drawdown, avg_trade_pl, profit_factor, sharpe_ratio, expectancy, max_consec_loss, avg_win, avg_loss, entry_ibs, exit_ibs, ledger_json))
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

def log_optimizer_run(strategy, ticker, timeframe, best_params, best_profit, best_win_rate, best_drawdown):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO optimizer_runs (timestamp, strategy, ticker, timeframe, best_params, best_profit, best_win_rate, best_drawdown)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), strategy, ticker, timeframe, best_params, best_profit, best_win_rate, best_drawdown))
    conn.commit()
    conn.close()

def get_all_optimizer_runs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM optimizer_runs ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Initialize on import
init_db()
