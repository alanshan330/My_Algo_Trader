import sys
import os
import pandas as pd
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.optimize_ibs import fetch_data

def main():
    state_file = os.path.join(os.path.dirname(__file__), "..", "ui_state.json")
    
    saved_csv = ""
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            saved_csv = state.get("csv_path", "")
    except Exception:
        pass
        
    if not saved_csv or not os.path.exists(saved_csv):
        print("Please set a valid CSV file in the UI first.")
        return

    # Load 5 years of data
    df, _, _ = fetch_data("NQ", "2020-01-01", "2026-01-01", saved_csv)
    df = df.dropna()
    for col in ['High','Low','Close']:
        df[col] = pd.to_numeric(df[col])
        
    # Calculate IBS
    ibs = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    df['IBS'] = ibs
    
    # We will use the robust universal parameters we found earlier: 0.35 Entry, 0.90 Exit
    ENTRY_IBS = 0.35
    EXIT_IBS = 0.90
    MULTIPLIER = 20 # NQ
    
    # Offsets to test (in points)
    offsets = [0, 10, 20, 30, 40, 50, 60, 80, 100]
    
    results = []
    
    for offset in offsets:
        in_trade = False
        contracts = 0
        total_cost = 0
        
        trades = 0
        winning_trades = 0
        total_pts = 0
        
        pending_order_price = None
        
        for i in range(len(df) - 1):
            today = df.iloc[i]
            tomorrow = df.iloc[i+1]
            
            # If we are holding a position, check for exit condition at TOMORROW'S close
            # We are mimicking daily resolution
            if contracts > 0:
                if tomorrow['IBS'] > EXIT_IBS:
                    # Sell at tomorrow's close
                    exit_price = tomorrow['Close']
                    pts = (exit_price * contracts) - total_cost
                    total_pts += pts
                    trades += 1
                    if pts > 0:
                        winning_trades += 1
                    contracts = 0
                    total_cost = 0
                    pending_order_price = None
            
            # If we are NOT in a position and not waiting on a pending order (or if we are averaging down? Let's just do single entry for this test to isolate the effect of the offset)
            if contracts == 0:
                if today['IBS'] < ENTRY_IBS:
                    # Signal fired today! Place limit order for tomorrow
                    pending_order_price = today['Close'] - offset
            
            # Check if pending order fills TOMORROW
            if pending_order_price is not None and contracts == 0:
                if tomorrow['Low'] <= pending_order_price:
                    # Filled!
                    # If it gapped down below our price, we get filled at the open.
                    # Otherwise, we get filled at our limit price.
                    fill_price = min(tomorrow['Open'], pending_order_price)
                    
                    contracts = 1
                    total_cost = fill_price
                    pending_order_price = None # Order consumed
                else:
                    # Order not filled. We cancel it.
                    pending_order_price = None
                    
        # Calculate summary
        win_rate = (winning_trades / trades * 100) if trades > 0 else 0
        results.append({
            "Limit Offset": f"{offset} pts",
            "Trades Executed": trades,
            "Missed/Skipped": "-",
            "Win Rate": f"{win_rate:.1f}%",
            "Total Pts": f"{total_pts:.1f}",
            "Total USD": f"${total_pts * MULTIPLIER:,.0f}"
        })
        
    res_df = pd.DataFrame(results)
    print("\n--- LIMIT ORDER OFFSET TEST (Entry 0.35, Exit 0.90) ---")
    print("If IBS < 0.35 today, place limit order at (Today's Close - Offset) for tomorrow.")
    print("If tomorrow's Low doesn't reach the offset, the trade is missed.\n")
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    main()
