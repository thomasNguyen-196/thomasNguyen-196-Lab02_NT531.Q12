import customtkinter


class LogPanel:
    def __init__(self, master, on_refresh, on_clear, on_save):
        self.frame = customtkinter.CTkFrame(master)
        self.frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=0)
        self.frame.grid_columnconfigure(3, weight=0)

        self.label = customtkinter.CTkLabel(self.frame, text="Logs", font=customtkinter.CTkFont(size=15, weight="bold"))
        self.label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.refresh_button = customtkinter.CTkButton(self.frame, text="Refresh", command=on_refresh, width=100)
        self.refresh_button.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="e")

        self.clear_button = customtkinter.CTkButton(self.frame, text="Clear", command=on_clear, width=80)
        self.clear_button.grid(row=0, column=2, padx=5, pady=(10, 5), sticky="e")

        self.save_button = customtkinter.CTkButton(self.frame, text="Save", command=on_save, width=80)
        self.save_button.grid(row=0, column=3, padx=5, pady=(10, 5), sticky="e")

        self.textbox = customtkinter.CTkTextbox(self.frame)
        self.textbox.grid(row=1, column=0, columnspan=4, padx=10, pady=(5, 10), sticky="nsew")
        self.textbox.configure(state="disabled")


