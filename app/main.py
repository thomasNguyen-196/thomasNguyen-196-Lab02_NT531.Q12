import customtkinter
import sys
import threading
from .ui.logging import TextboxStream as UiTextboxStream, configure_log_widget
from .ui.log_panel import LogPanel
from .controllers import AppBehaviorMixin


class App(AppBehaviorMixin, customtkinter.CTk):
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

        self._refresh_in_progress = False

        # Right-side log panel
        self.log_panel = LogPanel(self, self.on_refresh_click, self.on_log_clear_click, self.on_log_save_click)
        self.log_textbox = self.log_panel.textbox  # shim for existing logic

        # configure log tags (colors) via shared UI helper
        configure_log_widget(self.log_textbox)

        sys.stdout = UiTextboxStream(self)
        sys.stderr = UiTextboxStream(self)

        # Left-side panels
        self._build_network_frame()
        self._build_instance_frame()

        self.data_loading_thread = threading.Thread(target=self._load_data_and_update_ui, daemon=True)
        self.data_loading_thread.start()

    # All behavior methods are inherited from AppBehaviorMixin

if __name__ == "__main__":
    app = App()
    app.mainloop()
