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
        
    for exch in ['CME', 'GLOBEX', 'QO', 'NYBOT', 'ECBOT']:
        contract = ContFuture('NQ', exch)
        qualified = ib.qualifyContracts(contract)
        if qualified:
            print(f"SUCCESS with exchange: {exch}")
            print(qualified[0])
            break
        else:
            print(f"Failed with {exch}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if ib.isConnected():
        ib.disconnect()
