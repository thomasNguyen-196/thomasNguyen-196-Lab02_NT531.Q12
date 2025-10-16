import customtkinter


class TextboxStream:
    """A stream-like object that writes to a CTkTextbox via the hosting app."""
    def __init__(self, app):
        self.app = app

    def write(self, text):
        # Delegate to the app to handle parsing/coloring and thread-safety
        self.app.after(0, self.app._append_log, text)

    def flush(self):
        pass


def configure_log_widget(textbox: customtkinter.CTkTextbox):
    """Configure tags/colors for a CTkTextbox used as a log panel."""
    textbox.tag_config("INFO", foreground="#6b7280")      # gray-500
    textbox.tag_config("SUCCESS", foreground="#16a34a")   # green-600
    textbox.tag_config("WARNING", foreground="#d97706")   # amber-600
    textbox.tag_config("ERROR", foreground="#dc2626")     # red-600
    textbox.tag_config("POLL", foreground="#2563eb")      # blue-600
    textbox.tag_config("ROUTER", foreground="#7c3aed")    # violet-600
    textbox.tag_config("FLOATING", foreground="#0891b2")  # cyan-600
    textbox.tag_config("PORTS", foreground="#0ea5e9")     # sky-600
    textbox.tag_config("AUTH", foreground="#22c55e")      # green-500
    textbox.tag_config("UI", foreground="#a855f7")        # purple-500


def infer_log_tag(line: str):
    s = line.strip()
    if not s:
        return None
    if s.startswith("Error:"):
        return "ERROR"
    if s.startswith("Warning:"):
        return "WARNING"
    if s.startswith("Info:"):
        return "INFO"
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

