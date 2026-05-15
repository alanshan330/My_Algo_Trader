import re

with open("scripts/run_app.py", "r") as f:
    app_code = f.read()

# Add sma_200
sma_code = """
    atr = tr.rolling(window=14).mean()
    sma_200 = df['Close'].rolling(window=200).mean()
"""
app_code = re.sub(r"    atr = tr\.rolling\(window=14\)\.mean\(\)", sma_code.strip(), app_code)

# Add variables
vars_code = """
    is_points = "Points" in risk_type
    
    trend_filter = params.get("trend_filter", False)
    max_hold_days = params.get("max_hold_days", 0)
    max_contracts = params.get("max_contracts", 0)
    
    highest_high_since_entry = 0.0
    days_held = 0
"""
app_code = re.sub(r'    is_points = "Points" in risk_type\s+highest_high_since_entry = 0\.0', vars_code.strip(), app_code)

# Add days_held tick
tick_code = """
        current_atr = atr.iloc[i] if not pd.isna(atr.iloc[i]) else 1.0
        
        if contracts_held > 0:
            days_held += 1
"""
app_code = re.sub(r'        current_atr = atr\.iloc\[i\] if not pd\.isna\(atr\.iloc\[i\]\) else 1\.0', tick_code.strip(), app_code)

# Buy logic update
buy_code = """
        if current_ibs < entry_threshold:
            if not is_average_down and contracts_held > 0:
                pass # Already in position, don't average down
            elif trend_filter and current_close < sma_200.iloc[i]:
                pass # Blocked by 200 SMA Trend Filter
            elif max_contracts > 0 and contracts_held >= max_contracts:
                pass # Max contracts reached
            else:
                if contracts_held == 0:
                    highest_high_since_entry = current_close
                    days_held = 1
                contracts_held += 1
                total_cost += current_close
                log(f"[{current_date.strftime('%Y-%m-%d')}] BUY 1 Contract @ {current_close:.2f} (Total Held: {contracts_held})")
"""
app_code = re.sub(r'        if current_ibs < entry_threshold:.*?log\(f"\[\{current_date\.strftime.*?\] BUY 1 Contract.*?total_cost \+= current_close\n                log\(f"\[\{current_date\.strftime\(\'%Y-%m-%d\'\)\}\] BUY 1 Contract @ \{current_close:\.2f\} \(Total Held: \{contracts_held\}\)"\)', buy_code.strip(), app_code, flags=re.DOTALL)

# Exit logic update
exit_code = """
            if hit_tp or hit_sl:
                if hit_sl and hit_tp:
                    reason = "SL Hit (Ambiguous intraday crossover)"
                    exit_price = sl_price
                elif hit_sl:
                    reason = "SL Hit"
                    exit_price = sl_price
                else:
                    reason = "TP Hit"
                    exit_price = tp_price
                    
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "contracts": contracts_held,
                    "profit_pct": profit_pct,
                    "points": points_gained,
                    "dollars": dollar_gained
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] {reason}: SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue
                
            if max_hold_days > 0 and days_held > max_hold_days:
                exit_price = current_close
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "contracts": contracts_held,
                    "profit_pct": profit_pct,
                    "points": points_gained,
                    "dollars": dollar_gained
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] Stale Trade (Time Limit): SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
                continue
                
            if current_ibs > exit_threshold:
                exit_price = current_close
                points_gained = (exit_price * contracts_held) - total_cost
                dollar_gained = points_gained * multiplier
                profit_pct = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                
                trades.append({
                    "contracts": contracts_held,
                    "profit_pct": profit_pct,
                    "points": points_gained,
                    "dollars": dollar_gained
                })
                log(f"[{current_date.strftime('%Y-%m-%d')}] IBS Exit: SELL ALL {contracts_held} Contracts @ {exit_price:.2f} | Avg Entry: {avg_entry_price:.2f} | P/L: {points_gained:+.2f} pts (${dollar_gained:+.2f})\\n")
                
                contracts_held = 0
                total_cost = 0
                days_held = 0
"""
app_code = re.sub(r'            if hit_tp or hit_sl:.*?total_cost = 0', exit_code.strip(), app_code, flags=re.DOTALL)

# Also update the launch_params mapping for Lumibot
lumi_params = """
            "risk_type": launch_params.get("risk_type", "Percentage (%)"),
            "trend_filter": launch_params.get("trend_filter", False),
            "max_hold_days": launch_params.get("max_hold_days", 0),
            "max_contracts": launch_params.get("max_contracts", 0)
        }
"""
app_code = re.sub(r'            "risk_type": launch_params\.get\("risk_type", "Percentage \(%\)"\)\n        \}', lumi_params.strip(), app_code)

with open("scripts/run_app.py", "w") as f:
    f.write(app_code)

# -----------------
# -----------------
# Update Lumibot Strategy
with open("src/strategy/implementations/ibs_strategy.py", "r") as f:
    strat_code = f.read()
    
# Initialize days held
init_strat = """
        self.history_length = 2
        self.highest_high = 0.0
        self.entry_time = None
"""
strat_code = re.sub(r'        self\.history_length = 2\n        self\.highest_high = 0\.0', init_strat.strip(), strat_code)

# Setup variables inside execute
setup_strat = """
        is_atr = "ATR" in risk_type
        is_trailing = "Trailing" in risk_type
        
        trend_filter = self.parameters.get("trend_filter", False)
        max_hold_days = self.parameters.get("max_hold_days", 0)
        max_contracts = self.parameters.get("max_contracts", 0)
        
        current_atr = 1.0
"""
strat_code = re.sub(r'        is_atr = "ATR" in risk_type\n        is_trailing = "Trailing" in risk_type\n        \n        current_atr = 1\.0', setup_strat.strip(), strat_code)

# Check Trend Filter and Time based exit
check_strat = """
        if self.has_position():
            if self.entry_time is not None and max_hold_days > 0:
                days_held = (self.get_datetime() - self.entry_time).days
                if days_held > max_hold_days:
                    self.logger.info(f"Stale Trade! Held for {days_held} days > {max_hold_days} limit. Selling all.")
                    self.sell_all()
                    self.highest_high = 0.0
                    self.entry_time = None
                    return
            
            if current_price > self.highest_high:
"""
strat_code = re.sub(r'        if self\.has_position\(\):\n            if current_price > self\.highest_high:', check_strat.strip(), strat_code)

# Check max contracts and trend filter inside buy block
buy_strat = """
        # Check conditions
        if ibs < entry_threshold:
            if not is_average_down and self.has_position():
                self.logger.info(f"IBS {ibs:.4f} < {entry_threshold}, but we are already LONG (Single Entry Mode).")
                return
                
            if max_contracts > 0 and self.has_position():
                current_qty = self.get_position(self.symbol).quantity
                if current_qty >= max_contracts:
                    self.logger.info(f"Max Contracts ({max_contracts}) reached. Preventing further averaging down.")
                    return
                    
            if trend_filter:
                sma_bars = self.get_historical_prices(self.symbol, 200, "1D")
                if sma_bars is not None and len(sma_bars) >= 200:
                    sma_200 = sma_bars.df['close'].mean()
                    if current_price < sma_200:
                        self.logger.info(f"Price {current_price} < 200 SMA {sma_200}. Trend Filter blocking LONG entry.")
                        return
                
            self.logger.info(f"IBS {ibs:.4f} is below {entry_threshold}. Buying to average/enter LONG.")
            if not self.has_position():
                self.highest_high = current_price
                self.entry_time = self.get_datetime()
"""
strat_code = re.sub(r'        # Check conditions\n        if ibs < entry_threshold:.*?self\.highest_high = current_price', buy_strat.strip(), strat_code, flags=re.DOTALL)

with open("src/strategy/implementations/ibs_strategy.py", "w") as f:
    f.write(strat_code)
