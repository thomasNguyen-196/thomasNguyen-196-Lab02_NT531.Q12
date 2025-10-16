import customtkinter


class InstancePanel:
    def __init__(self, master, on_create, on_flavor_select):
        self.frame = customtkinter.CTkFrame(master)
        self.frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.frame.grid_columnconfigure(1, weight=1)

        title = customtkinter.CTkLabel(self.frame, text="Instance", font=customtkinter.CTkFont(weight="bold"))
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        loading_values = ["Loading..."]
        customtkinter.CTkLabel(self.frame, text="Images").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.image_combo = customtkinter.CTkComboBox(self.frame, values=loading_values)
        self.image_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Flavors").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.flavor_combo = customtkinter.CTkComboBox(self.frame, values=loading_values, command=on_flavor_select)
        self.flavor_combo.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        self.flavor_details_label = customtkinter.CTkLabel(self.frame, text="", anchor="w", justify="left")
        self.flavor_details_label.grid(row=3, column=1, padx=10, pady=(0, 5), sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Security Group").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.sg_combo = customtkinter.CTkComboBox(self.frame, values=loading_values)
        self.sg_combo.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Network").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.network_combo = customtkinter.CTkComboBox(self.frame, values=loading_values)
        self.network_combo.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Floating IP").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.floating_ip_combo = customtkinter.CTkComboBox(self.frame, values=loading_values)
        self.floating_ip_combo.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Name").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.instance_name_entry = customtkinter.CTkEntry(self.frame, placeholder_text="tung196_TEST_INSTANCE")
        self.instance_name_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.frame, text="Custom Script").grid(row=8, column=0, padx=10, pady=5, sticky="nw")
        self.script_textbox = customtkinter.CTkTextbox(self.frame, height=100)
        self.script_textbox.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

        self.create_button = customtkinter.CTkButton(self.frame, text="Create", command=on_create)
        self.create_button.grid(row=9, column=1, padx=10, pady=10, sticky="e")


