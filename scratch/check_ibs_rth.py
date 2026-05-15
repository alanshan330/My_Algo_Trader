import nest_asyncio
nest_asyncio.apply()
import logging
from ib_insync import IB, ContFuture

ib = IB()
try:
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    contract = ContFuture('NQ', 'CME')
    ib.qualifyContracts(contract)
    
    print("--- RTH = True ---")
    bars_rth = ib.reqHistoricalData(
        contract, endDateTime='',
        durationStr='10 D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    for bar in bars_rth:
        if bar.date.strftime("%Y-%m-%d") == "2026-04-29":
            print(f"High={bar.high:.2f}, Low={bar.low:.2f}, Close={bar.close:.2f}")

    print("--- MIDPOINT ---")
    bars_mid = ib.reqHistoricalData(
        contract, endDateTime='',
        durationStr='10 D',
        barSizeSetting='1 day',
        whatToShow='MIDPOINT',
        useRTH=False,
        formatDate=1
    )
    for bar in bars_mid:
        if bar.date.strftime("%Y-%m-%d") == "2026-04-29":
            print(f"High={bar.high:.2f}, Low={bar.low:.2f}, Close={bar.close:.2f}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if ib.isConnected():
        ib.disconnect()
