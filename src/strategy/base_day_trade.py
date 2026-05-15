from lumibot.strategies.strategy import Strategy
from datetime import timedelta
import logging
from src.utils.logger import get_logger

class BaseDayTradeStrategy(Strategy):
    """
    Abstract base class for day trading strategies.
    Handles common logic like position sizing and EOD liquidation.
    """
    
    def initialize(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # Configuration parsed from UI/config
        self.symbol = self.parameters.get("symbol", "SPY")
        self.cash_at_risk = self.parameters.get("cash_at_risk", 0.5)
        self.sleeptime = self.parameters.get("sleep_time", "1D")
        
        # Risk management
        self.minutes_before_close = 15
        
        # Hook for custom subclass initialization
        self.custom_initialize()

    def custom_initialize(self):
        """Override this in subclasses for specific initialization logic"""
        pass

    def on_trading_iteration(self):
        """
        Main Lumibot trading loop.
        We wrap the custom logic to ensure end-of-day liquidation safety.
        """
        # Day Trading Safety Check: Close positions before the end of the day
        # Only relevant if we are actually day trading (intraday timeframe)
        # For daily timeframes, we hold overnight, so we skip this check.
        if "M" in self.sleeptime or "m" in self.sleeptime:
            time_to_close = self.get_time_to_market_close()
            if time_to_close is not None and time_to_close < timedelta(minutes=self.minutes_before_close):
                if self.has_position():
                    self.logger.info(f"Market closes in less than {self.minutes_before_close} mins. Liquidating all positions.")
                    self.sell_all()
                return # Skip custom logic if we are about to close
                
        # Run the specific strategy logic
        self.execute_strategy()

    def execute_strategy(self):
        """
        Override this method in subclasses to implement the actual trading logic.
        """
        raise NotImplementedError("Subclasses must implement execute_strategy()")

    def calculate_position_size(self, current_price: float) -> int:
        """ Calculate how many shares to buy based on cash_at_risk """
        cash = self.cash
        cash_to_invest = cash * self.cash_at_risk
        quantity = int(cash_to_invest // current_price)
        return quantity

    def has_position(self) -> bool:
        """ Check if we currently hold shares of the symbol """
        position = self.get_position(self.symbol)
        return position is not None and position.quantity > 0
