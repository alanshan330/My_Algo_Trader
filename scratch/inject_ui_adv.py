import re

with open("src/ui/launcher.py", "r") as f:
    ui_code = f.read()

# 1. Inject Advanced Risk Management UI
adv_risk_ui = """
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

        # Custom CSV Data Source"""

ui_code = re.sub(r'# Custom CSV Data Source', adv_risk_ui.strip(), ui_code)

# 2. Bump rows for elements after row 13
def row_bumper(match):
    prefix = match.group(1)
    row_num = int(match.group(2))
    suffix = match.group(3)
    if row_num >= 13:
        return f"{prefix}{row_num + 2}{suffix}"
    return match.group(0)

# We need to apply row bumper only to the lines after the injection
parts = ui_code.split("# Custom CSV Data Source")
if len(parts) == 2:
    parts[1] = re.sub(r'(\.grid\(row=)(\d+)(,)', row_bumper, parts[1])
    ui_code = "# Custom CSV Data Source".join(parts)

# 3. Inject params parsing
param_parse = """
        try:
            max_hold = int(self.max_hold_input.get().strip())
        except ValueError:
            max_hold = 0
            
        try:
            max_cont = int(self.max_contracts_input.get().strip())
        except ValueError:
            max_cont = 0
            
        trend_filter = self.trend_filter_var.get()
        use_rth = self.rth_var.get()"""
ui_code = re.sub(r'use_rth = self.rth_var.get\(\)', param_parse.strip(), ui_code)

# Add to dictionaries
ui_code = re.sub(r'"use_rth": use_rth', '"use_rth": use_rth,\n            "trend_filter": trend_filter,\n            "max_hold_days": max_hold,\n            "max_contracts": max_cont', ui_code)

with open("src/ui/launcher.py", "w") as f:
    f.write(ui_code)
