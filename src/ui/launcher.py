import customtkinter as ctk
import tkinter.filedialog as fd
from tkcalendar import DateEntry
from typing import Dict, Any
from datetime import datetime, timedelta
import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "ui_state.json")

class TradingLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI & Algo Trading Bot Launcher")
        self.geometry("450x700")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.launch_params: Dict[str, Any] = {}
        
        # Load previous state
        self.saved_state = self.load_state()
        
        # Title
        self.title_label = ctk.CTkLabel(self.main_frame, text="Trading Bot Setup", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Ticker Input
        self.ticker_label = ctk.CTkLabel(self.main_frame, text="Target Ticker (e.g., QQQ, SPY, NQ):")
        self.ticker_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.ticker_entry = ctk.CTkEntry(self.main_frame, placeholder_text="QQQ")
        self.ticker_entry.insert(0, self.saved_state.get("ticker", "QQQ"))
        self.ticker_entry.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Timeframe Selection
        self.tf_label = ctk.CTkLabel(self.main_frame, text="Timeframe:")
        self.tf_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.timeframes = ["1 min", "5 mins", "15 mins", "30 mins", "1 hour", "4 hours", "1 day"]
        self.tf_combobox = ctk.CTkComboBox(self.main_frame, values=self.timeframes)
        self.tf_combobox.set(self.saved_state.get("timeframe", "1 day"))
        self.tf_combobox.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Date Range Selection
        self.date_label = ctk.CTkLabel(self.main_frame, text="Backtest Date Range:")
        self.date_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.date_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.date_frame.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.date_frame.grid_columnconfigure((0, 1), weight=1)
        
        default_end = datetime.now()
        default_start = default_end - timedelta(days=365*3)
        
        # Parse dates from state if available
        try:
            saved_start = datetime.strptime(self.saved_state.get("start_date", ""), "%Y-%m-%d")
        except:
            saved_start = default_start
            
        try:
            saved_end = datetime.strptime(self.saved_state.get("end_date", ""), "%Y-%m-%d")
        except:
            saved_end = default_end
        
        self.start_date_label = ctk.CTkLabel(self.date_frame, text="Start:")
        self.start_date_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        
        # tkcalendar DateEntry for Start Date
        self.start_date_input = DateEntry(self.date_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_input.set_date(saved_start)
        self.start_date_input.grid(row=1, column=0, padx=(0, 5), sticky="ew", pady=(0, 5))
        
        self.end_date_label = ctk.CTkLabel(self.date_frame, text="End:")
        self.end_date_label.grid(row=0, column=1, padx=(5, 0), sticky="w")
        
        # tkcalendar DateEntry for End Date
        self.end_date_input = DateEntry(self.date_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_input.set_date(saved_end)
        self.end_date_input.grid(row=1, column=1, padx=(5, 0), sticky="ew", pady=(0, 5))

        # Strategy Selection
        self.strategy_label = ctk.CTkLabel(self.main_frame, text="Trading Strategy:")
        self.strategy_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="w")
        self.strategies = ["IBS Strategy (Single Entry)", "IBS Strategy (Average Down)"]
        self.strategy_combobox = ctk.CTkComboBox(self.main_frame, values=self.strategies)
        self.strategy_combobox.set(self.saved_state.get("strategy", "IBS Strategy (Average Down)"))
        self.strategy_combobox.grid(row=8, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Custom IBS Thresholds
        self.threshold_label = ctk.CTkLabel(self.main_frame, text="Custom IBS Thresholds:")
        self.threshold_label.grid(row=9, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.threshold_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.threshold_frame.grid(row=10, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.threshold_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.entry_ibs_label = ctk.CTkLabel(self.threshold_frame, text="Entry (e.g. 0.18):")
        self.entry_ibs_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.entry_ibs_input = ctk.CTkEntry(self.threshold_frame, placeholder_text="0.18")
        self.entry_ibs_input.insert(0, self.saved_state.get("entry_ibs", "0.18"))
        self.entry_ibs_input.grid(row=1, column=0, padx=(0, 5), sticky="ew")
        
        self.exit_ibs_label = ctk.CTkLabel(self.threshold_frame, text="Exit (e.g. 0.84):")
        self.exit_ibs_label.grid(row=0, column=1, padx=(5, 0), sticky="w")
        self.exit_ibs_input = ctk.CTkEntry(self.threshold_frame, placeholder_text="0.84")
        self.exit_ibs_input.insert(0, self.saved_state.get("exit_ibs", "0.84"))
        self.exit_ibs_input.grid(row=1, column=1, padx=(5, 0), sticky="ew")

        # Stop Loss & Take Profit
        self.sl_tp_label = ctk.CTkLabel(self.main_frame, text="Risk Management (0 = Off):")
        self.sl_tp_label.grid(row=11, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.sl_tp_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.sl_tp_frame.grid(row=12, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.sl_tp_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.risk_type_var = ctk.StringVar(value=self.saved_state.get("risk_type", "Percentage (%)"))
        self.risk_type_menu = ctk.CTkOptionMenu(self.sl_tp_frame, variable=self.risk_type_var, values=["Percentage (%)", "Points (pts)", "ATR Stop", "Trailing ATR (Chandelier)"])
        self.risk_type_menu.grid(row=0, column=0, columnspan=2, padx=(0, 0), pady=(0, 10), sticky="ew")
        
        self.tp_label = ctk.CTkLabel(self.sl_tp_frame, text="Take Profit (0=Off):")
        self.tp_label.grid(row=1, column=0, padx=(0, 5), sticky="w")
        self.tp_input = ctk.CTkEntry(self.sl_tp_frame, placeholder_text="Value / ATR Multiplier")
        self.tp_input.insert(0, self.saved_state.get("take_profit", "0.0"))
        self.tp_input.grid(row=2, column=0, padx=(0, 5), sticky="ew")
        
        self.sl_label = ctk.CTkLabel(self.sl_tp_frame, text="Stop Loss (0=Off):")
        self.sl_label.grid(row=1, column=1, padx=(5, 0), sticky="w")
        self.sl_input = ctk.CTkEntry(self.sl_tp_frame, placeholder_text="Value / ATR Multiplier")
        self.sl_input.insert(0, self.saved_state.get("stop_loss", "0.0"))
        self.sl_input.grid(row=2, column=1, padx=(5, 0), sticky="ew")

        # Advanced Risk Management
        self.adv_risk_label = ctk.CTkLabel(self.main_frame, text="Advanced Filters (Mean Reversion):")
        self.adv_risk_label.grid(row=13, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.adv_risk_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.adv_risk_frame.grid(row=14, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.adv_risk_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.trend_filter_var = ctk.BooleanVar(value=self.saved_state.get("trend_filter", False))
        self.trend_filter_switch = ctk.CTkSwitch(self.adv_risk_frame, text="200-SMA Trend Filter", variable=self.trend_filter_var)
        self.trend_filter_switch.grid(row=0, column=0, columnspan=2, padx=(0, 0), pady=(0, 10), sticky="w")
        
        self.max_hold_label = ctk.CTkLabel(self.adv_risk_frame, text="Max Hold Days:")
        self.max_hold_label.grid(row=1, column=0, padx=(0, 5), sticky="w")
        self.max_hold_input = ctk.CTkEntry(self.adv_risk_frame, placeholder_text="0 (Unlimited)")
        self.max_hold_input.insert(0, self.saved_state.get("max_hold_days", "0"))
        self.max_hold_input.grid(row=2, column=0, padx=(0, 5), sticky="ew")
        
        self.max_contracts_label = ctk.CTkLabel(self.adv_risk_frame, text="Max Contracts:")
        self.max_contracts_label.grid(row=1, column=1, padx=(5, 0), sticky="w")
        self.max_contracts_input = ctk.CTkEntry(self.adv_risk_frame, placeholder_text="0 (Unlimited)")
        self.max_contracts_input.insert(0, self.saved_state.get("max_contracts", "0"))
        self.max_contracts_input.grid(row=2, column=1, padx=(5, 0), sticky="ew")

        # Custom CSV Data Source
        self.csv_label = ctk.CTkLabel(self.main_frame, text="Data Source (Optional CSV for Futures):")
        self.csv_label.grid(row=15, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.csv_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.csv_frame.grid(row=16, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.csv_frame.grid_columnconfigure(0, weight=1)
        
        self.csv_path_var = ctk.StringVar(value=self.saved_state.get("csv_path", ""))
        self.csv_entry = ctk.CTkEntry(self.csv_frame, textvariable=self.csv_path_var, placeholder_text="Leave blank to use Alpaca API")
        self.csv_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.browse_btn = ctk.CTkButton(self.csv_frame, text="Browse", width=60, command=self.browse_csv)
        self.browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Mode Selection
        self.mode_label = ctk.CTkLabel(self.main_frame, text="Execution Mode:")
        self.mode_label.grid(row=17, column=0, padx=20, pady=(10, 0), sticky="w")
        self.mode_var = ctk.StringVar(value=self.saved_state.get("mode", "backtest"))
        
        self.radio_bt = ctk.CTkRadioButton(self.main_frame, text="Backtest (Historical)", variable=self.mode_var, value="backtest")
        self.radio_bt.grid(row=18, column=0, padx=20, pady=(5, 0), sticky="w")
        
        self.radio_live = ctk.CTkRadioButton(self.main_frame, text="Live Paper Trading", variable=self.mode_var, value="live")
        self.radio_live.grid(row=19, column=0, padx=20, pady=(5, 0), sticky="w")
        
        self.radio_optimize = ctk.CTkRadioButton(self.main_frame, text="Parameter Sweep Optimizer", variable=self.mode_var, value="optimize")
        self.radio_optimize.grid(row=20, column=0, padx=20, pady=(5, 10), sticky="w")
        
        self.rth_var = ctk.BooleanVar(value=self.saved_state.get("use_rth", False))
        self.rth_switch = ctk.CTkSwitch(self.main_frame, text="Regular Trading Hours (RTH) Only", variable=self.rth_var)
        self.rth_switch.grid(row=21, column=0, padx=20, pady=(5, 20), sticky="w")

        # Start Button
        self.start_button = ctk.CTkButton(self.main_frame, text="Launch Trading Engine", command=self.on_start, height=40)
        self.start_button.grid(row=22, column=0, padx=20, pady=20, sticky="ew")

    def load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_state(self, state_dict: Dict[str, Any]):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state_dict, f, indent=4)
        except Exception as e:
            print(f"Failed to save UI state: {e}")

    def browse_csv(self):
        filepath = fd.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if filepath:
            self.csv_path_var.set(filepath)

    def on_start(self):
        ticker = self.ticker_entry.get().strip() or "QQQ"
        timeframe = self.tf_combobox.get()
        mode = self.mode_var.get()
        strategy = self.strategy_combobox.get()
        csv_path = self.csv_path_var.get().strip()
        
        start_date = self.start_date_input.get()
        end_date = self.end_date_input.get()
        
        try:
            entry_val = float(self.entry_ibs_input.get().strip())
        except ValueError:
            entry_val = 0.18
            
        try:
            exit_val = float(self.exit_ibs_input.get().strip())
        except ValueError:
            exit_val = 0.84

        try:
            tp_val = float(self.tp_input.get().strip())
        except ValueError:
            tp_val = 0.0
            
        try:
            sl_val = float(self.sl_input.get().strip())
        except ValueError:
            sl_val = 0.0

        try:
            max_hold = int(self.max_hold_input.get().strip())
        except ValueError:
            max_hold = 0
            
        try:
            max_cont = int(self.max_contracts_input.get().strip())
        except ValueError:
            max_cont = 0
            
        trend_filter = self.trend_filter_var.get()
        use_rth = self.rth_var.get()
        risk_type = self.risk_type_var.get()

        self.launch_params = {
            "symbol": ticker.upper(),
            "sleep_time": timeframe,
            "mode": mode,
            "strategy": strategy,
            "entry_threshold": entry_val,
            "exit_threshold": exit_val,
            "take_profit": tp_val,
            "stop_loss": sl_val,
            "risk_type": risk_type,
            "start_date": start_date,
            "end_date": end_date,
            "csv_path": csv_path,
            "use_rth": use_rth,
            "trend_filter": trend_filter,
            "max_hold_days": max_hold,
            "max_contracts": max_cont
        }
        
        # Save state for next time
        self.save_state({
            "ticker": ticker.upper(),
            "timeframe": timeframe,
            "mode": mode,
            "strategy": strategy,
            "entry_ibs": str(entry_val),
            "exit_ibs": str(exit_val),
            "take_profit": str(tp_val),
            "stop_loss": str(sl_val),
            "risk_type": risk_type,
            "start_date": start_date,
            "end_date": end_date,
            "csv_path": csv_path,
            "use_rth": use_rth,
            "trend_filter": trend_filter,
            "max_hold_days": max_hold,
            "max_contracts": max_cont
        })
        
        self.destroy()

def get_launch_parameters() -> Dict[str, Any]:
    ctk.set_appearance_mode("dark")
    app = TradingLauncher()
    app.mainloop()
    return app.launch_params

if __name__ == "__main__":
    params = get_launch_parameters()
    print("Launch parameters:", params)
