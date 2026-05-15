from src.strategy.base_day_trade import BaseDayTradeStrategy

class IBSStrategy(BaseDayTradeStrategy):
    """
    Internal Bar Strength (IBS) Strategy
    
    Logic:
    IBS = (Close - Low) / (High - Low)
    Long Entry: When IBS < 0.18 (Price closed near its daily low, mean reversion expected)
    Long Exit: When IBS > 0.84 (Price closed near its daily high)
    """

    def custom_initialize(self):
        # We need at least 1 day of historical data to calculate IBS
self.history_length = 2
        self.highest_high = 0.0
        self.entry_time = None

    def execute_strategy(self):
        # Fetch recent historical bars
        bars = self.get_historical_prices(self.symbol, self.history_length, self.sleeptime)
        
        if bars is None or len(bars) < 1:
            self.logger.info("Not enough historical data to calculate IBS.")
            return

        # Get the most recently completed bar
        # If we are running daily, this is yesterday's full bar or today's current bar depending on execution time.
        # Lumibot gives us a pandas dataframe
        df = bars.df
        latest_bar = df.iloc[-1]
        
        high = latest_bar['high']
        low = latest_bar['low']
        close = latest_bar['close']
        
        if high == low:
            # Avoid division by zero
            return
            
        ibs = (close - low) / (high - low)
        current_price = self.get_last_price(self.symbol)
        
        self.logger.info(f"Current IBS for {self.symbol}: {ibs:.4f}")

        # Dynamic Thresholds
        entry_threshold = self.parameters.get("entry_threshold", 0.18)
        exit_threshold = self.parameters.get("exit_threshold", 0.84)
        
        is_average_down = self.parameters.get("is_average_down", True)
        tp_val = self.parameters.get("take_profit", 0.0)
        sl_val = self.parameters.get("stop_loss", 0.0)
        risk_type = self.parameters.get("risk_type", "Percentage (%)")
        is_points = "Points" in risk_type
is_atr = "ATR" in risk_type
        is_trailing = "Trailing" in risk_type
        
        trend_filter = self.parameters.get("trend_filter", False)
        max_hold_days = self.parameters.get("max_hold_days", 0)
        max_contracts = self.parameters.get("max_contracts", 0)
        
        current_atr = 1.0
        if is_atr:
            import pandas as pd
            hist_bars = self.get_historical_prices(self.symbol, 15, self.sleeptime)
            if hist_bars is not None and len(hist_bars) > 1:
                hist_df = hist_bars.df
                tr1 = hist_df['high'] - hist_df['low']
                tr2 = (hist_df['high'] - hist_df['close'].shift(1)).abs()
                tr3 = (hist_df['low'] - hist_df['close'].shift(1)).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(14).mean()
                current_atr = atr.iloc[-1]
                if pd.isna(current_atr):
                    current_atr = 1.0

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
                self.highest_high = current_price
                
            if is_trailing and sl_val > 0:
                trail_sl_price = self.highest_high - (current_atr * sl_val)
                if current_price <= trail_sl_price:
                    self.logger.info(f"Trailing ATR (Chandelier) Stop Hit! Selling all at {current_price}")
                    self.sell_all()
                    self.highest_high = 0.0
                    return
        
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
                
            quantity = self.calculate_position_size(current_price)
            if quantity > 0:
                tp_price = None
                sl_price = None
                
                if is_atr:
                    if tp_val > 0:
                        tp_price = current_price + (current_atr * tp_val)
                    if sl_val > 0 and not is_trailing:
                        sl_price = current_price - (current_atr * sl_val)
                elif is_points:
                    if tp_val > 0:
                        tp_price = current_price + tp_val
                    if sl_val > 0:
                        sl_price = current_price - sl_val
                else:
                    if tp_val > 0:
                        tp_price = current_price * (1 + (tp_val/100.0))
                    if sl_val > 0:
                        sl_price = current_price * (1 - (sl_val/100.0))
                    
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="market",
                    take_profit_price=tp_price,
                    stop_loss_price=sl_price
                )
                self.submit_order(order)
                
        elif self.has_position() and ibs > exit_threshold:
            self.logger.info(f"IBS {ibs:.4f} is above {exit_threshold}. Exiting all LONG positions.")
            self.sell_all()
            self.highest_high = 0.0
