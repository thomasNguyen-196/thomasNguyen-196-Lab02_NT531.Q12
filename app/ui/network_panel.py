import customtkinter


class NetworkPanel:
    def __init__(self, master, on_create):
        self.frame = customtkinter.CTkFrame(master)
        self.frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.frame.grid_columnconfigure(1, weight=1)

        title = customtkinter.CTkLabel(self.frame, text="Network", font=customtkinter.CTkFont(weight="bold"))
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        customtkinter.CTkLabel(self.frame, text="Network name").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.network_name_entry = customtkinter.CTkEntry(self.frame, placeholder_text="tung196_test_network")
        self.network_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Subnet Name").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.subnet_name_entry = customtkinter.CTkEntry(self.frame, placeholder_text="tung196_test_subnet")
        self.subnet_name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Network Address").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.network_address_entry = customtkinter.CTkEntry(self.frame, placeholder_text="192.168.11.0/24")
        self.network_address_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Router Name").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.router_name_entry = customtkinter.CTkEntry(self.frame, placeholder_text="tung196_router")
        self.router_name_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        self.auto_router_var = customtkinter.BooleanVar(value=True)
        self.auto_router_checkbox = customtkinter.CTkCheckBox(
            self.frame,
            text="Create router & attach subnet",
            variable=self.auto_router_var,
            onvalue=True,
            offvalue=False,
        )
        self.auto_router_checkbox.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.create_button = customtkinter.CTkButton(self.frame, text="Create", command=on_create)
        self.create_button.grid(row=6, column=1, padx=10, pady=10, sticky="e")


