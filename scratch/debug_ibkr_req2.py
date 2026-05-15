import nest_asyncio
nest_asyncio.apply()
import logging
from ib_insync import IB, ContFuture, util
from datetime import datetime

util.logToConsole(logging.DEBUG)

ib = IB()
try:
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    contract = ContFuture('NQ', 'CME')
    ib.qualifyContracts(contract)
    
    end_date = datetime(2026, 5, 5)
    
    bars = ib.reqHistoricalData(
        contract, endDateTime=end_date.strftime("%Y%m%d 23:59:59"),
        durationStr='123 D',
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
