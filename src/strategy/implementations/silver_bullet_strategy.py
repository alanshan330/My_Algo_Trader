from src.strategy.base_day_trade import BaseDayTradeStrategy
from lumibot.entities import Order
import pytz

class ICTSilverBulletStrategy(BaseDayTradeStrategy):
    """
    ICT Silver Bullet Strategy
    
    Rules:
    1. Only trade during specific macro time windows (e.g., 10:00 - 11:00 AM EST).
    2. Look for a Fair Value Gap (FVG) formation.
    3. Enter when price retraces into the FVG.
    4. Stop loss placed below/above the FVG generating candle.
    5. Take profit set at fixed RR or next liquidity pool.
    """
    
    def custom_initialize(self):
        # Time windows for the silver bullet (in EST)
        self.sb_morning_start = 10
        self.sb_morning_end = 11
        
        # Risk / Reward parameters
        self.risk_reward_ratio = self.parameters.get("risk_reward", 2.0)
        
        # State tracking
        self.active_fvg = None # None, 'bullish', or 'bearish'
        self.fvg_entry_price = 0.0
        self.fvg_stop_loss = 0.0
        self.fvg_take_profit = 0.0
        
        self.logger.info("ICT Silver Bullet Strategy Initialized")

    def execute_strategy(self):
        # We need minute or 5-minute data
        bars = self.get_historical_prices(self.symbol, 10, self.sleeptime)
        if bars is None or len(bars.df) < 3:
            return
            
        df = bars.df
        
        # Check if we have an open position
        if self.has_position():
            # Let the platform's native stop-loss/take-profit brackets handle exits,
            # or we could manually monitor them here if needed.
            return
            
        # Ensure we are in the EST timezone for the time window check
        current_dt = self.get_datetime().astimezone(pytz.timezone('America/New_York'))
        
        # Check if we are inside the Silver Bullet time window (10:00 AM - 11:00 AM)
        is_silver_bullet_window = (current_dt.hour == self.sb_morning_start)
        
        if not is_silver_bullet_window:
            # Clear active FVGs outside the window
            self.active_fvg = None
            return
            
        current_price = self.get_last_price(self.symbol)
        
        # We look for a Fair Value Gap in the last 3 closed candles
        # C1 (index -3), C2 (index -2), C3 (index -1)
        # Note: In backtesting, if the current bar is not closed, we use -4, -3, -2.
        # But `bars.df` usually returns closed bars up to current time depending on the backend.
        
        c1 = df.iloc[-3]
        c2 = df.iloc[-2]
        c3 = df.iloc[-1]
        
        # Identify Bullish FVG: C1 High < C3 Low
        if c1['high'] < c3['low']:
            self.active_fvg = 'bullish'
            self.fvg_entry_price = c3['low'] # Top of the gap
            self.fvg_stop_loss = c1['low']   # Below the swing
            
            risk = self.fvg_entry_price - self.fvg_stop_loss
            if risk > 0:
                self.fvg_take_profit = self.fvg_entry_price + (risk * self.risk_reward_ratio)
                
        # Identify Bearish FVG: C1 Low > C3 High
        elif c1['low'] > c3['high']:
            self.active_fvg = 'bearish'
            self.fvg_entry_price = c3['high'] # Bottom of the gap
            self.fvg_stop_loss = c1['high']   # Above the swing
            
            risk = self.fvg_stop_loss - self.fvg_entry_price
            if risk > 0:
                self.fvg_take_profit = self.fvg_entry_price - (risk * self.risk_reward_ratio)
                
        # If we have an active FVG, check if price has retraced into it for entry
        if self.active_fvg == 'bullish':
            if current_price <= self.fvg_entry_price and current_price > self.fvg_stop_loss:
                # Retraced into bullish FVG - Buy
                quantity = self.calculate_position_size(current_price)
                if quantity > 0:
                    order = self.create_order(
                        self.symbol, quantity, "buy", 
                        take_profit_price=self.fvg_take_profit,
                        stop_loss_price=self.fvg_stop_loss
                    )
                    self.submit_order(order)
                    self.logger.info(f"Entered Bullish Silver Bullet. Entry: {current_price}, Stop: {self.fvg_stop_loss}, TP: {self.fvg_take_profit}")
                    self.active_fvg = None # Reset after entry
                    
        elif self.active_fvg == 'bearish':
            if current_price >= self.fvg_entry_price and current_price < self.fvg_stop_loss:
                # Retraced into bearish FVG - Sell Short
                quantity = self.calculate_position_size(current_price)
                if quantity > 0:
                    order = self.create_order(
                        self.symbol, quantity, "sell", 
                        take_profit_price=self.fvg_take_profit,
                        stop_loss_price=self.fvg_stop_loss
                    )
                    self.submit_order(order)
                    self.logger.info(f"Entered Bearish Silver Bullet. Entry: {current_price}, Stop: {self.fvg_stop_loss}, TP: {self.fvg_take_profit}")
                    self.active_fvg = None # Reset after entry
