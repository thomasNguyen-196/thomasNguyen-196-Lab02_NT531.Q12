import base64
import customtkinter
import json
import sys
import threading
import time
from tkinter import filedialog as tk_filedialog
from .services.poll_resources import poll_openstack_resources
from .services.create_net_subnet import create_network, create_subnet
from .services.auth import get_openstack_token
from .services.create_instance import create_instance
from .services.router_fip import (
    create_router,
    add_subnet_interface,
    associate_floating_ip,
    get_ports_for_device,
)
from .utils.validate import (
    is_instance_duplicate,
    is_network_duplicate,
    get_available_floating_ips,
    get_port_id_by_device,
)


class TextboxStream:
    """A stream-like object that writes to a CTkTextbox."""
    def __init__(self, app):
        self.textbox = app.log_textbox
        self.app = app

    def write(self, text):
        # delegate to app for parsing and colorizing
        self.app.after(0, self.app._append_log, text)

    def flush(self):
        pass

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.data = {}
        self._floating_ip_map = {}
        self.no_floating_ip_option = "No floating IP (skip)"
        self.poll_log_path = "poll_refresh.log"
        self.title("Main Application")
        self.geometry("1280x880")
        self.minsize(1280, 880)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.controls_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_rowconfigure(1, weight=1)

        self.log_frame = customtkinter.CTkFrame(self)
        self.log_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(1, weight=0)
        self.log_frame.grid_columnconfigure(2, weight=0)
        self.log_frame.grid_columnconfigure(3, weight=0)
        self._refresh_in_progress = False

        log_label = customtkinter.CTkLabel(self.log_frame, text="Logs", font=customtkinter.CTkFont(size=15, weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.refresh_button = customtkinter.CTkButton(self.log_frame, text="Refresh", command=self.on_refresh_click, width=100)
        self.refresh_button.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="e")
        self.clear_log_button = customtkinter.CTkButton(self.log_frame, text="Clear", command=self.on_log_clear_click, width=80)
        self.clear_log_button.grid(row=0, column=2, padx=5, pady=(10, 5), sticky="e")
        self.save_log_button = customtkinter.CTkButton(self.log_frame, text="Save", command=self.on_log_save_click, width=80)
        self.save_log_button.grid(row=0, column=3, padx=5, pady=(10, 5), sticky="e")
        self.log_textbox = customtkinter.CTkTextbox(self.log_frame)
        self.log_textbox.grid(row=1, column=0, columnspan=4, padx=10, pady=(5, 10), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # configure log tags (colors)
        # note: CTkTextbox proxies standard tkinter Text tag config API
        self.log_textbox.tag_config("INFO", foreground="#6b7280")  # gray-500
        self.log_textbox.tag_config("SUCCESS", foreground="#16a34a")  # green-600
        self.log_textbox.tag_config("WARNING", foreground="#d97706")  # amber-600
        self.log_textbox.tag_config("ERROR", foreground="#dc2626")  # red-600
        self.log_textbox.tag_config("POLL", foreground="#2563eb")  # blue-600
        self.log_textbox.tag_config("ROUTER", foreground="#7c3aed")  # violet-600
        self.log_textbox.tag_config("FLOATING", foreground="#0891b2")  # cyan-600
        self.log_textbox.tag_config("PORTS", foreground="#0ea5e9")  # sky-600
        self.log_textbox.tag_config("AUTH", foreground="#22c55e")  # green-500
        self.log_textbox.tag_config("UI", foreground="#a855f7")  # purple-500

        sys.stdout = TextboxStream(self)
        sys.stderr = TextboxStream(self)

        self._build_network_frame()
        self._build_instance_frame(loading=True)

        self.data_loading_thread = threading.Thread(target=self._load_data_and_update_ui, daemon=True)
        self.data_loading_thread.start()

    def _toggle_buttons(self, enabled):
        """Enable or disable the create buttons."""
        state = "normal" if enabled else "disabled"
        self.create_network_button.configure(state=state)
        self.create_instance_button.configure(state=state)
        if state == "disabled":
            self.refresh_button.configure(state="disabled")
        elif not self._refresh_in_progress:
            self.refresh_button.configure(state="normal")

    def on_log_clear_click(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def on_log_save_click(self):
        # open save dialog; default filename includes timestamp
        filename = tk_filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="openstack_gui.log"
        )
        if not filename:
            return
        content = self.log_textbox.get("1.0", "end")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Info: Log saved to {filename}")
        except OSError as exc:
            print(f"Error: Failed to save log file: {exc}")

    def _append_log(self, text):
        # Parse incoming text into lines and colorize by simple rules
        if not text:
            return
        lines = text.splitlines(keepends=True)
        self.log_textbox.configure(state="normal")
        for line in lines:
            tag = self._infer_log_tag(line)
            if tag:
                self.log_textbox.insert("end", line, tag)
            else:
                self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _infer_log_tag(self, line):
        s = line.strip()
        if not s:
            return None
        # explicit prefixes
        if s.startswith("Error:"):
            return "ERROR"
        if s.startswith("Warning:"):
            return "WARNING"
        if s.startswith("Info:"):
            return "INFO"
        # component tags used by services
        if s.startswith("[poll]"):
            return "POLL"
        if s.startswith("[router]"):
            return "ROUTER"
        if s.startswith("[floating-ip]"):
            return "FLOATING"
        if s.startswith("[ports]"):
            return "PORTS"
        if s.startswith("[auth]"):
            return "AUTH"
        if s.startswith("[ui]"):
            return "UI"
        # success heuristics
        lowered = s.lower()
        if "success" in lowered or "successful" in lowered:
            return "SUCCESS"
        if "failed" in lowered or "exception" in lowered:
            return "ERROR"
        if "warning" in lowered:
            return "WARNING"
        if "info" in lowered:
            return "INFO"
        return None

    def on_refresh_click(self):
        if self._refresh_in_progress:
            return
        print("--- Refresh button clicked ---")
        self._refresh_in_progress = True
        self.refresh_button.configure(state="disabled")

        def _refresh_logic():
            self._force_poll_and_update_ui(on_finish_callback=self._on_refresh_complete)

        threading.Thread(target=_refresh_logic, daemon=True).start()

    def _on_refresh_complete(self):
        print("Refresh complete.")
        self._refresh_in_progress = False
        if (
            self.create_network_button.cget("state") == "normal"
            and self.create_instance_button.cget("state") == "normal"
        ):
            self.refresh_button.configure(state="normal")

    def on_create_network_click(self):
        print("--- Create Network button clicked ---")
        self._toggle_buttons(enabled=False)

        def _thread_logic():
            try:
                network_name = self.network_name_entry.get()
                if not network_name:
                    print("Error: Network name cannot be empty.")
                    self._toggle_buttons(enabled=True)
                    return
                
                if is_network_duplicate(network_name):
                    print(f"Error: Network '{network_name}' already exists.")
                    self._toggle_buttons(enabled=True)
                    return

                token = get_openstack_token()
                network_id = create_network(token, network_name)

                if network_id:
                    print(f"Network creation successful. ID: {network_id}")
                    subnet_name = self.subnet_name_entry.get()
                    cidr = self.network_address_entry.get()

                    if subnet_name and cidr:
                        subnet_id = create_subnet(token, subnet_name, network_id, cidr)
                        if subnet_id:
                            print(f"Subnet creation successful. ID: {subnet_id}")

                            if self.auto_router_var.get():
                                router_name = self.router_name_entry.get().strip() or f"{network_name}_router"
                                router_id = create_router(token, router_name)
                                if router_id:
                                    attach_result = add_subnet_interface(token, router_id, subnet_id)
                                    if attach_result:
                                        print(f"Router '{router_name}' created and subnet attached. ID: {router_id}")
                                    else:
                                        print(f"Warning: Router '{router_name}' created but failed to attach subnet.")
                                else:
                                    print(f"Warning: Failed to create router '{router_name}'.")

                            # clear fields
                            self.network_name_entry.delete(0, "end")
                            self.subnet_name_entry.delete(0, "end")
                            self.network_address_entry.delete(0, "end")
                            self.router_name_entry.delete(0, "end")
                        else:
                            print("Subnet creation failed.")
                    else:
                        print("Warning: Missing subnet info; only network created.")
                        if self.auto_router_var.get():
                            print("Info: Skipping router creation because subnet information is incomplete.")
                else:
                    print("Network creation failed.")

            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            self._force_poll_and_update_ui()

            # Set the network combobox in the instance frame to the newly created network (for user convenience)
            network_names = [net.get('name', 'Unnamed') for net in self.data.get("networks", {}).get("networks", [])]
            if network_name in network_names:
                self.network_combo.set(network_name)
                print(f"Set network combobox to newly created network: {network_name}")
            else:
                # If not found in cached data, set directly
                self.network_combo.set(network_name)

            self._toggle_buttons(enabled=True)

        # Chạy tất cả trên luồng riêng
        threading.Thread(target=_thread_logic, daemon=True).start()


    def on_create_instance_click(self):
        print("--- Create Instance button clicked ---")
        self._toggle_buttons(enabled=False)
        def _actual_action():
            try:
                instance_name = self.instance_name_entry.get()
                if not instance_name:
                    print("Error: Instance name cannot be empty.")
                    return
                
                if is_instance_duplicate(instance_name):
                    print(f"Error: Instance '{instance_name}' already exists.")
                    self._toggle_buttons(enabled=True)
                    return

                selected_image_name = self.image_combo.get()
                selected_flavor_string = self.flavor_combo.get()
                selected_sg_name = self.sg_combo.get()
                selected_network_name = self.network_combo.get()
                selected_floating_value = self.floating_ip_combo.get()
                floating_ip_id = self._floating_ip_map.get(selected_floating_value)

                if not all([selected_image_name, selected_flavor_string, selected_sg_name, selected_network_name]):
                    print("Error: Please ensure all fields are selected/filled.")
                    return

                selected_flavor_name = selected_flavor_string.split(" (")[0]

                image_id = None
                for img in self.data.get("images", {}).get("images", []):
                    if img.get("name") == selected_image_name:
                        image_id = img.get("id")
                        break

                flavor_id = None
                for f in self.data.get("flavors", {}).get("flavors", []):
                    if f.get("name") == selected_flavor_name:
                        flavor_id = f.get("id")
                        break

                network_id = None
                for net in self.data.get("networks", {}).get("networks", []):
                    if net.get("name") == selected_network_name:
                        network_id = net.get("id")
                        break

                if not all([image_id, flavor_id, network_id]):
                    print("Error: Could not find IDs for the selected resources.")
                    return

                user_script = self.script_textbox.get("1.0", "end").strip()
                if user_script:
                    user_data_b64 = base64.b64encode(user_script.encode('utf-8')).decode('utf-8')
                else:
                    user_data_b64 = None

                token = get_openstack_token()
                
                instance_id = create_instance(token, instance_name, image_id, flavor_id, network_id, user_data=user_data_b64)

                if instance_id:
                    print(f"Instance creation successful. ID: {instance_id}")

                    if floating_ip_id:
                        print(f"Attempting to associate floating IP ID {floating_ip_id} with instance {instance_id}...")
                        print("Waiting 5 seconds for instance networking to initialize...")
                        time.sleep(5)
                        print("Refreshing cached inventory prior to floating IP association...")
                        self._force_poll_and_update_ui()
                        port_id = None
                        ports = get_ports_for_device(token, instance_id)
                        for port in ports:
                            candidate_port_id = port.get("id")
                            if candidate_port_id:
                                port_id = candidate_port_id
                                break

                        if not port_id:
                            print("Info: No ports returned from live query, falling back to refreshed cache.")
                            port_id = get_port_id_by_device(instance_id)

                        if port_id:
                            association = associate_floating_ip(token, floating_ip_id, port_id)
                            if association:
                                floating_ip_address = (
                                    association.get("floatingip", {}).get("floating_ip_address") or selected_floating_value
                                )
                                print(f"Floating IP {floating_ip_address} associated successfully.")
                            else:
                                print(f"Warning: Failed to associate floating IP {floating_ip_id} with port {port_id}.")
                        else:
                            print(f"Warning: Could not determine port for instance {instance_id}; skipping floating IP assignment.")
                    else:
                        if selected_floating_value != self.no_floating_ip_option:
                            print(f"Warning: Selected floating IP '{selected_floating_value}' not available in map; skipping assignment.")

                    # Clear fields
                    self.instance_name_entry.delete(0, "end")
                    self.script_textbox.delete("1.0", "end")
                else:
                    print("Instance creation failed.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            self._force_poll_and_update_ui()
            self._toggle_buttons(enabled=True)

        threading.Thread(target=_actual_action, daemon=True).start()

    def _build_network_frame(self):
        self.network_frame = customtkinter.CTkFrame(self.controls_frame)
        self.network_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.network_frame.grid_columnconfigure(1, weight=1)
        network_title = customtkinter.CTkLabel(self.network_frame, text="Network", font=customtkinter.CTkFont(weight="bold"))
        network_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")
        customtkinter.CTkLabel(self.network_frame, text="Network name").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.network_name_entry = customtkinter.CTkEntry(self.network_frame, placeholder_text="tung196_test_network")
        self.network_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.network_frame, text="Subnet Name").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.subnet_name_entry = customtkinter.CTkEntry(self.network_frame, placeholder_text="tung196_test_subnet")
        self.subnet_name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.network_frame, text="Network Address").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.network_address_entry = customtkinter.CTkEntry(self.network_frame, placeholder_text="192.168.11.0/24")
        self.network_address_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.network_frame, text="Router Name").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.router_name_entry = customtkinter.CTkEntry(self.network_frame, placeholder_text="tung196_router")
        self.router_name_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.auto_router_var = customtkinter.BooleanVar(value=True)
        self.auto_router_checkbox = customtkinter.CTkCheckBox(
            self.network_frame,
            text="Create router & attach subnet",
            variable=self.auto_router_var,
            onvalue=True,
            offvalue=False,
        )
        self.auto_router_checkbox.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.create_network_button = customtkinter.CTkButton(self.network_frame, text="Create", command=self.on_create_network_click)
        self.create_network_button.grid(row=6, column=1, padx=10, pady=10, sticky="e")

    def _build_instance_frame(self, loading=False):
        self.instance_frame = customtkinter.CTkFrame(self.controls_frame)
        self.instance_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.instance_frame.grid_columnconfigure(1, weight=1)
        instance_title = customtkinter.CTkLabel(self.instance_frame, text="Instance", font=customtkinter.CTkFont(weight="bold"))
        instance_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        loading_values = ["Loading..."]
        customtkinter.CTkLabel(self.instance_frame, text="Images").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.image_combo = customtkinter.CTkComboBox(self.instance_frame, values=loading_values)
        self.image_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Flavors").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.flavor_combo = customtkinter.CTkComboBox(self.instance_frame, values=loading_values, command=self._on_flavor_select)
        self.flavor_combo.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.flavor_details_label = customtkinter.CTkLabel(self.instance_frame, text="", anchor="w", justify="left")
        self.flavor_details_label.grid(row=3, column=1, padx=10, pady=(0, 5), sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Security Group").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.sg_combo = customtkinter.CTkComboBox(self.instance_frame, values=loading_values)
        self.sg_combo.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Network").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.network_combo = customtkinter.CTkComboBox(self.instance_frame, values=loading_values)
        self.network_combo.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Floating IP").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.floating_ip_combo = customtkinter.CTkComboBox(self.instance_frame, values=loading_values)
        self.floating_ip_combo.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Name").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.instance_name_entry = customtkinter.CTkEntry(self.instance_frame, placeholder_text="tung196_TEST_INSTANCE")
        self.instance_name_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.instance_frame, text="Custom Script").grid(row=8, column=0, padx=10, pady=5, sticky="nw")
        self.script_textbox = customtkinter.CTkTextbox(self.instance_frame, height=100)
        self.script_textbox.grid(row=8, column=1, padx=10, pady=5, sticky="ew")
        self.create_instance_button = customtkinter.CTkButton(self.instance_frame, text="Create", command=self.on_create_instance_click)
        self.create_instance_button.grid(row=9, column=1, padx=10, pady=10, sticky="e")

    def _load_data_and_update_ui(self):
        try:
            with open("openstack_data.json", "r", encoding='utf-8') as f:
                self.data = json.load(f)
                print("Data loaded from cache.")
        except FileNotFoundError:
            print("Cached data not found. Polling from OpenStack API...")
            poll_openstack_resources(verbose=False, log_file=self.poll_log_path)
            try:
                with open("openstack_data.json", "r", encoding='utf-8') as f:
                    self.data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error: Failed to load data after polling: {e}")
        except json.JSONDecodeError as e:
            print(f"Warning: Could not decode cached JSON data: {e}")
        self.after(0, self._update_comboboxes)

    def _force_poll_and_update_ui(self, on_finish_callback=None):
        """Runs in a background thread to FORCE a poll and then updates the UI."""
        poll_openstack_resources(verbose=False, log_file=self.poll_log_path)
        try:
            with open("openstack_data.json", "r", encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Failed to load data after polling: {e}")
            self.data = {}
        self.after(0, self._update_comboboxes, on_finish_callback)

    def _update_comboboxes(self, on_finish_callback=None):
        """Updates the comboboxes with data. Must run on the main thread."""
        print("Updating UI with loaded data...")
        image_names = [img.get('name', 'Unnamed') for img in self.data.get("images", {}).get("images", [])]
        self.image_combo.configure(values=image_names if image_names else ["No images found"])
        self.image_combo.set(image_names[0] if image_names else "No images found")

        flavor_display_list = []
        flavors = self.data.get("flavors", {}).get("flavors", [])
        for f in flavors:
            ram_mb = f.get('ram', 0)
            ram_gb = ram_mb / 1024 if ram_mb else 0
            vcpus = f.get('vcpus', 'N/A')
            disk = f.get('disk', 'N/A')
            display_name = f"{f.get('name')} (VCPUs: {vcpus}, RAM: {ram_gb:.2f}GB, Disk: {disk}GB)"
            flavor_display_list.append(display_name)

        self.flavor_combo.configure(values=flavor_display_list if flavor_display_list else ["No flavors found"], command=self._on_flavor_select)
        self.flavor_combo.set(flavor_display_list[0] if flavor_display_list else "No flavors found")

        sg_names = [sg.get('name', 'Unnamed') for sg in self.data.get("security_groups", {}).get("security_groups", [])]
        self.sg_combo.configure(values=sg_names if sg_names else ["No SGs found"])
        if "default" in sg_names:
            self.sg_combo.set("default")
        else:
            self.sg_combo.set(sg_names[0] if sg_names else "No SGs found")

        network_names = [net.get('name', 'Unnamed') for net in self.data.get("networks", {}).get("networks", [])]
        self.network_combo.configure(values=network_names if network_names else ["No networks found"])
        self.network_combo.set(network_names[0] if network_names else "No networks found")

        available_fips = get_available_floating_ips()
        floating_values = [self.no_floating_ip_option]
        self._floating_ip_map = {}
        for ip in available_fips:
            address = ip.get("floating_ip_address", "Unknown IP")
            ip_id = ip.get("id", "")
            display = f"{address} ({ip_id[:8]})" if ip_id else address
            floating_values.append(display)
            self._floating_ip_map[display] = ip_id

        if len(floating_values) == 1:
            print("Info: No available floating IPs detected in cache.")

        self.floating_ip_combo.configure(values=floating_values)
        self.floating_ip_combo.set(floating_values[0])
        
        self._on_flavor_select(self.flavor_combo.get())
        print("UI update complete.")

        if on_finish_callback:
            self.after(50, on_finish_callback)

    def _on_flavor_select(self, selected_flavor_string):
        """Callback function for when a flavor is selected from the combobox."""
        if not self.data or not selected_flavor_string or "(" not in selected_flavor_string:
            self.flavor_details_label.configure(text="")
            return
        
        selected_flavor_name = selected_flavor_string.split(" (")[0]
        
        flavor_details = None
        for flavor in self.data.get("flavors", {}).get("flavors", []) :
            if flavor.get("name") == selected_flavor_name:
                flavor_details = flavor
                break
        
        if flavor_details:
            ram_mb = flavor_details.get('ram', 0)
            ram_gb = ram_mb / 1024 if ram_mb else 0
            vcpus = flavor_details.get('vcpus', 'N/A')
            disk = flavor_details.get('disk', 'N/A')
            details_text = f"VCPUs: {vcpus}, RAM: {ram_gb:.2f} GB, Disk: {disk} GB"
            self.flavor_details_label.configure(text=details_text)
        else:
            self.flavor_details_label.configure(text="(Details not found)")

if __name__ == "__main__":
    app = App()
    app.mainloop()
