import yfinance as yf
from datetime import datetime
import pandas as pd

try:
    df = yf.download("QQQ", start="2026-04-25", end="2026-05-02", progress=False)
    if hasattr(df.columns, 'droplevel'):
        df.columns = df.columns.droplevel(1)
        
    for index, row in df.iterrows():
        if index.strftime("%Y-%m-%d") == "2026-04-29":
            high = row['High']
            low = row['Low']
            close = row['Close']
            ibs = (close - low) / (high - low)
            print(f"QQQ (Yahoo Finance) on 2026-04-29: High={high:.2f}, Low={low:.2f}, Close={close:.2f} => IBS = {ibs:.4f}")
            break
except Exception as e:
    print(f"YF Error: {e}")

try:
    import nest_asyncio
    nest_asyncio.apply()
    from ib_insync import IB, ContFuture, util
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    contract = ContFuture('NQ', 'CME')
    ib.qualifyContracts(contract)
    bars = ib.reqHistoricalData(
        contract, endDateTime='',
        durationStr='10 D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=False,
        formatDate=1
    )
    ib.disconnect()
    for bar in bars:
        if bar.date.strftime("%Y-%m-%d") == "2026-04-29":
            high = bar.high
            low = bar.low
            close = bar.close
            ibs = (close - low) / (high - low)
            print(f"NQ (IBKR) on 2026-04-29: High={high:.2f}, Low={low:.2f}, Close={close:.2f} => IBS = {ibs:.4f}")
            break
except Exception as e:
    print(f"IBKR Error: {e}")
