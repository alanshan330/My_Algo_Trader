with open('scripts/run_app.py', 'r') as f:
    content = f.read()

# Add ledger = [] right after trades = []
content = content.replace('    trades = []', '    trades = []\n    ledger = []')

# Add to ledger for BUY
buy_log = "log(f\"[{current_date.strftime('%Y-%m-%d')}] BUY 1 Contract @ {current_close:.2f} (Total Held: {contracts_held})\")"
buy_ledger = '''log(f"[{current_date.strftime('%Y-%m-%d')}] BUY 1 Contract @ {current_close:.2f} (Total Held: {contracts_held})")
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "BUY",
                    "Contracts": 1,
                    "Price": round(current_close, 2),
                    "Total Held": contracts_held,
                    "Avg Entry": "",
                    "P/L Pts": "",
                    "P/L USD": "",
                    "Reason": ""
                })'''
content = content.replace(buy_log, buy_ledger)

# Now, we need to modify the 3 SELL ALL places
import re

# We will just replace trades.append with ledger.append and update the fields!
# But wait, `trades` is still needed for final summary calculations (Win Rate, Total Return, etc.)
# So we need to keep `trades.append` AND add `ledger.append`.

def inject_ledger(match):
    original = match.group(0)
    # Extract the reason string directly from the trades dict
    # But it's easier to just build it:
    
    # We will just append ledger.append right after trades.append
    ledger_str = '''
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": "TP/SL" if "reason" in locals() else ("Time Limit" if "Stale" in str(current_close) else "IBS Exit")
                })'''
    return original + ledger_str

# Wait, `reason` variable exists for TP/SL, but not for Time Limit or IBS Exit.
# Let's do it manually.

tp_sl_trades = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": reason,
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''

tp_sl_ledger = tp_sl_trades + '''
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": reason
                })'''
content = content.replace(tp_sl_trades, tp_sl_ledger)

time_trades = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "Time Limit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''
time_ledger = time_trades + '''
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": "Time Limit"
                })'''
content = content.replace(time_trades, time_ledger)

ibs_trades = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "IBS Exit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''
ibs_ledger = ibs_trades + '''
                ledger.append({
                    "Date": current_date.strftime('%Y-%m-%d'),
                    "Action": "SELL ALL",
                    "Contracts": contracts_held,
                    "Price": round(exit_price, 2),
                    "Total Held": 0,
                    "Avg Entry": round(avg_entry_price, 2),
                    "P/L Pts": round(points_gained, 2),
                    "P/L USD": round(dollar_gained, 2),
                    "Reason": "IBS Exit"
                })'''
content = content.replace(ibs_trades, ibs_ledger)


# Update return statement to return ledger instead of trades!
content = content.replace('return "\\n".join(output), []', 'return "\\n".join(output), [], []')
content = content.replace('return "\\n".join(output), trades', 'return "\\n".join(output), trades, ledger')

# Update main function signature
content = content.replace('report_text, trades_list = run_pandas_backtest(launch_params)', 'report_text, trades_list, ledger = run_pandas_backtest(launch_params)')

# Update CSV export to use ledger
content = content.replace('pd.DataFrame(trades_list).to_csv(csv_path, index=False)', 'pd.DataFrame(ledger).to_csv(csv_path, index=False)')

with open('scripts/run_app.py', 'w') as f:
    f.write(content)

print("Done")
