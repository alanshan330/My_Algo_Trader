import nest_asyncio
nest_asyncio.apply()
from ib_insync import IB, ContFuture

ib = IB()
try:
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)
    except:
        ib.connect('127.0.0.1', 7496, clientId=99)
        
    contract = ContFuture('NQ', 'CME')
    ib.qualifyContracts(contract)
    
    shows = ['TRADES', 'MIDPOINT', 'BID', 'ASK', 'BID_ASK', 'ADJUSTED_LAST', 'HISTORICAL_VOLATILITY', 'OPTION_IMPLIED_VOLATILITY']
    for show in shows:
        try:
            bars = ib.reqHistoricalData(
                contract, endDateTime='',
                durationStr='10 D',
                barSizeSetting='1 day',
                whatToShow=show,
                useRTH=False,
                formatDate=1
            )
            for bar in bars:
                if bar.date.strftime("%Y-%m-%d") == "2026-04-29":
                    print(f"{show}: High={bar.high:.2f}, Low={bar.low:.2f}, Close={bar.close:.2f}")
        except:
            pass
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if ib.isConnected():
        ib.disconnect()
