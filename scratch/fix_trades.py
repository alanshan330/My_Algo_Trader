import re

with open('scripts/run_app.py', 'r') as f:
    content = f.read()

# Fix trades dict to be detailed
old_dict = '''                trades.append({
                    "contracts": contracts_held,
                    "profit_pct": profit_pct,
                    "points": points_gained,
                    "dollars": dollar_gained
                })'''

new_dict_tp_sl = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": reason,
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''

new_dict_time = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "Time Limit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''

new_dict_ibs = '''                trades.append({
                    "Exit Date": current_date.strftime('%Y-%m-%d'),
                    "Reason": "IBS Exit",
                    "Contracts": contracts_held,
                    "Avg Entry": round(avg_entry_price, 2),
                    "Exit Price": round(exit_price, 2),
                    "Profit %": round(profit_pct, 2),
                    "Points": round(points_gained, 2),
                    "Dollars": round(dollar_gained, 2)
                })'''

if content.count(old_dict) == 3:
    content = content.replace(old_dict, new_dict_tp_sl, 1)
    content = content.replace(old_dict, new_dict_time, 1)
    content = content.replace(old_dict, new_dict_ibs, 1)
    print('Replaced dicts')
else:
    print('Failed to replace dicts, found count:', content.count(old_dict))

content = content.replace('return "\\n".join(output)', 'return "\\n".join(output), trades', 1)

with open('scripts/run_app.py', 'w') as f:
    f.write(content)
