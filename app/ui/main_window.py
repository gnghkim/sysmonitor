import queue
import customtkinter as ctk
from app.core.collector import Collector
from app.core.settings import AppSettings, load_settings, save_settings
from app.ui.tab_overview import OverviewTab
from app.ui.tab_processes import ProcessesTab
from app.ui.tab_settings import SettingsTab


class MainWindow(ctk.CTk):
    def __init__(self):
        self._settings = load_settings()
        ctk.set_appearance_mode(self._settings.theme)
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("SysMonitor")
        self.geometry("900x650")
        self.minsize(700, 500)

        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._collector = Collector(self._queue, self._settings)

        self._build_ui()
        self._collector.start()
        self._poll()

    def _build_ui(self):
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=10, pady=10)

        for name in ("Overview", "Processes", "Settings"):
            self._tabs.add(name)

        self._overview = OverviewTab(self._tabs.tab("Overview"))
        self._overview.pack(fill="both", expand=True)

        self._processes = ProcessesTab(self._tabs.tab("Processes"))
        self._processes.pack(fill="both", expand=True)

        self._settings_tab = SettingsTab(
            self._tabs.tab("Settings"),
            self._settings,
            on_change=self._apply_settings,
        )
        self._settings_tab.pack(fill="both", expand=True)

        start = "Overview" if self._settings.start_tab == "overview" else "Processes"
        self._tabs.set(start)

    def _poll(self):
        try:
            stats = self._queue.get_nowait()
            self._overview.update(stats)
            self._processes.update(stats.processes)
        except queue.Empty:
            pass
        self.after(500, self._poll)

    def _apply_settings(self, new: AppSettings):
        self._settings = new
        save_settings(new)
        self._collector._settings = new
        ctk.set_appearance_mode(new.theme)

    def on_closing(self):
        self._collector.stop()
        self.destroy()
