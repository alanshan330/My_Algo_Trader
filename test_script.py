import requests
import traceback
try:
    res = requests.post('http://127.0.0.1:5000/api/chart_data', json={
        'ticker': 'NQ',
        'timeframe': '5 mins'
    })
    data = res.json()
    chart_data = data.get('data', [])
    print(f"Got {len(chart_data)} chart bars")

    backtest_params = {
        'mode': 'backtest', 
        'symbol': 'NQ', 
        'timeframe': '5 mins', 
        'strategy': 'ICT Silver Bullet', 
        'start_date': '2026-05-01', 
        'end_date': '2026-05-17', 
        'chart_data': chart_data
    }
    res2 = requests.post('http://127.0.0.1:5000/api/backtest', json=backtest_params)
    print(res2.json())
except Exception as e:
    traceback.print_exc()
