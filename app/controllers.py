import base64
import json
import threading
import time
from tkinter import filedialog as tk_filedialog

from .ui.logging import infer_log_tag as ui_infer_log_tag
from .ui.network_panel import NetworkPanel
from .ui.instance_panel import InstancePanel
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


class AppBehaviorMixin:
    def _toggle_buttons(self, enabled):
        state = "normal" if enabled else "disabled"
        self.create_network_button.configure(state=state)
        self.create_instance_button.configure(state=state)
        if state == "disabled":
            self.log_panel.refresh_button.configure(state="disabled")
        elif not self._refresh_in_progress:
            self.log_panel.refresh_button.configure(state="normal")

    def on_log_clear_click(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def on_log_save_click(self):
        filename = tk_filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="openstack_gui.log",
        )
        if not filename:
            return
        content = self.log_panel.textbox.get("1.0", "end")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Info: Log saved to {filename}")
        except OSError as exc:
            print(f"Error: Failed to save log file: {exc}")

    def _append_log(self, text):
        if not text:
            return
        lines = text.splitlines(keepends=True)
        self.log_panel.textbox.configure(state="normal")
        for line in lines:
            tag = self._infer_log_tag(line)
            if tag:
                self.log_panel.textbox.insert("end", line, tag)
            else:
                self.log_panel.textbox.insert("end", line)
        self.log_panel.textbox.see("end")
        self.log_panel.textbox.configure(state="disabled")

    def _infer_log_tag(self, line):
        return ui_infer_log_tag(line)

    def on_refresh_click(self):
        if self._refresh_in_progress:
            return
        print("--- Refresh button clicked ---")
        self._refresh_in_progress = True
        self.log_panel.refresh_button.configure(state="disabled")

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
            self.log_panel.refresh_button.configure(state="normal")

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

            network_names = [net.get('name', 'Unnamed') for net in self.data.get("networks", {}).get("networks", [])]
            if network_name in network_names:
                self.network_combo.set(network_name)
                print(f"Set network combobox to newly created network: {network_name}")
            else:
                self.network_combo.set(network_name)

            self._toggle_buttons(enabled=True)

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
        self.network_panel = NetworkPanel(self.controls_frame, self.on_create_network_click)
        self.network_frame = self.network_panel.frame
        self.network_name_entry = self.network_panel.network_name_entry
        self.subnet_name_entry = self.network_panel.subnet_name_entry
        self.network_address_entry = self.network_panel.network_address_entry
        self.router_name_entry = self.network_panel.router_name_entry
        self.auto_router_var = self.network_panel.auto_router_var
        self.create_network_button = self.network_panel.create_button

    def _build_instance_frame(self):
        self.instance_panel = InstancePanel(self.controls_frame, self.on_create_instance_click, self._on_flavor_select)
        self.instance_frame = self.instance_panel.frame
        self.image_combo = self.instance_panel.image_combo
        self.flavor_combo = self.instance_panel.flavor_combo
        self.flavor_details_label = self.instance_panel.flavor_details_label
        self.sg_combo = self.instance_panel.sg_combo
        self.network_combo = self.instance_panel.network_combo
        self.floating_ip_combo = self.instance_panel.floating_ip_combo
        self.instance_name_entry = self.instance_panel.instance_name_entry
        self.script_textbox = self.instance_panel.script_textbox
        self.create_instance_button = self.instance_panel.create_button

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
        poll_openstack_resources(verbose=False, log_file=self.poll_log_path)
        try:
            with open("openstack_data.json", "r", encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Failed to load data after polling: {e}")
            self.data = {}
        self.after(0, self._update_comboboxes, on_finish_callback)

    def _update_comboboxes(self, on_finish_callback=None):
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


