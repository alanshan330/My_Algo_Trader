import re

with open("src/ui/launcher.py", "r") as f:
    content = f.read()

# 1. Add scrollable frame
init_code = """
        self.title("AI & Algo Trading Bot Launcher")
        self.geometry("450x700")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.launch_params: Dict[str, Any] = {}
"""

content = re.sub(
    r'        self\.title\("AI & Algo Trading Bot Launcher"\).*?self\.launch_params: Dict\[str, Any\] = \{\}',
    init_code.strip(),
    content,
    flags=re.DOTALL
)

# 2. Replace parent of widgets from `self` to `self.main_frame`
content = re.sub(r'ctk\.CTkLabel\(self,', r'ctk.CTkLabel(self.main_frame,', content)
content = re.sub(r'ctk\.CTkEntry\(self,', r'ctk.CTkEntry(self.main_frame,', content)
content = re.sub(r'ctk\.CTkComboBox\(self,', r'ctk.CTkComboBox(self.main_frame,', content)
content = re.sub(r'ctk\.CTkFrame\(self,', r'ctk.CTkFrame(self.main_frame,', content)
content = re.sub(r'ctk\.CTkRadioButton\(self,', r'ctk.CTkRadioButton(self.main_frame,', content)
content = re.sub(r'ctk\.CTkSwitch\(self,', r'ctk.CTkSwitch(self.main_frame,', content)
content = re.sub(r'ctk\.CTkButton\(self,', r'ctk.CTkButton(self.main_frame,', content)

with open("src/ui/launcher.py", "w") as f:
    f.write(content)
