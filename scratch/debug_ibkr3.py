import nest_asyncio
nest_asyncio.apply()
import logging
from ib_insync import IB, ContFuture, util

util.logToConsole(logging.ERROR)

ib = IB()
try:
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    for sym in ['ES', 'RTY', 'YM']:
        for exch in ['CME', 'GLOBEX', 'CBOT']:
            contract = ContFuture(sym, exch)
            qualified = ib.qualifyContracts(contract)
            if qualified:
                print(f"SUCCESS {sym} -> {exch}")
                break
except Exception as e:
    print(f"Error: {e}")
finally:
    if ib.isConnected():
        ib.disconnect()
