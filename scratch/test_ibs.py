import yfinance as yf
import pandas as pd
from datetime import datetime

df = yf.download("NQ=F", start="2026-01-01", end="2026-05-04", progress=False)

# handle multiindex
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)

df = df.dropna()
df['IBS'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])

print("--- IBS < 0.18 YTD ---")
entries = df[df['IBS'] < 0.18]
for date, row in entries.iterrows():
    print(f"{date.strftime('%Y-%m-%d')} : IBS={row['IBS']:.3f} (C={row['Close']:.2f}, L={row['Low']:.2f}, H={row['High']:.2f})")

print(f"Total entries found: {len(entries)}")
