import yfinance as yf
import pandas as pd

df = yf.download("NQ=F", start="2026-01-01", end="2026-05-05", progress=False)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)

df = df.dropna()
df['IBS'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])

in_pos = False
entry_date = None
for i in range(len(df)):
    row = df.iloc[i]
    date = df.index[i]
    
    if not in_pos:
        if row['IBS'] < 0.18:
            in_pos = True
            entry_date = date
            print(f"ENTER: {date.strftime('%Y-%m-%d')} (IBS: {row['IBS']:.2f})")
    else:
        if row['IBS'] > 0.84:
            in_pos = False
            print(f"  EXIT: {date.strftime('%Y-%m-%d')} (IBS: {row['IBS']:.2f}) - Held {(date - entry_date).days} days")
