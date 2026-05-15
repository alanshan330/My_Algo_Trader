import nest_asyncio
nest_asyncio.apply()
import logging
from ib_insync import IB, ContFuture, util

util.logToConsole(logging.DEBUG)

ib = IB()
try:
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    contract = ContFuture('NQ', 'CME')
    ib.qualifyContracts(contract)
    print("Qualified:", contract)
    
    print("Requesting...")
    bars = ib.reqHistoricalData(
        contract, endDateTime='',
        durationStr='10 D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=False,
        formatDate=1
    )
    print(f"Bars: {len(bars)}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if ib.isConnected():
        ib.disconnect()
