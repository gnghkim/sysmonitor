from collections import deque
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.models.system_stats import SystemStats

MAX_POINTS = 60


class OverviewTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._cpu_history: deque[float] = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
        self._mem_history: deque[float] = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
        self._build_ui()

    def _build_ui(self):
        metrics = ctk.CTkFrame(self)
        metrics.pack(fill="x", padx=10, pady=(10, 5))
        metrics.columnconfigure(1, weight=1)

        self._cpu_bar, self._cpu_lbl = self._make_bar(metrics, "CPU", 0)
        self._mem_bar, self._mem_lbl = self._make_bar(metrics, "RAM", 1)
        self._bat_bar, self._bat_lbl = self._make_bar(metrics, "Battery", 2)

        fig = Figure(figsize=(8, 3), dpi=90, facecolor="#1e1e1e")
        self._ax_cpu = fig.add_subplot(2, 1, 1)
        self._ax_mem = fig.add_subplot(2, 1, 2)
        self._style_ax(self._ax_cpu, "CPU %")
        self._style_ax(self._ax_mem, "RAM %")
        self._line_cpu, = self._ax_cpu.plot(list(self._cpu_history), color="#4fc3f7", linewidth=1.5)
        self._line_mem, = self._ax_mem.plot(list(self._mem_history), color="#81c784", linewidth=1.5)
        fig.tight_layout(pad=1.2)

        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=10, pady=(5, 10))
        self._lbl_temp = ctk.CTkLabel(stats_row, text="온도: --")
        self._lbl_temp.pack(side="left", padx=10)
        self._lbl_disk = ctk.CTkLabel(stats_row, text="디스크: --")
        self._lbl_disk.pack(side="left", padx=10)
        self._lbl_net = ctk.CTkLabel(stats_row, text="네트워크: --")
        self._lbl_net.pack(side="left", padx=10)
        self._lbl_bat_detail = ctk.CTkLabel(stats_row, text="")
        self._lbl_bat_detail.pack(side="right", padx=10)

    def _make_bar(self, parent, label: str, row: int) -> tuple:
        ctk.CTkLabel(parent, text=label, width=70, anchor="w").grid(
            row=row, column=0, padx=(10, 5), pady=4, sticky="w"
        )
        bar = ctk.CTkProgressBar(parent)
        bar.grid(row=row, column=1, padx=5, pady=4, sticky="ew")
        bar.set(0)
        lbl = ctk.CTkLabel(parent, text="0%", width=55, anchor="e")
        lbl.grid(row=row, column=2, padx=(5, 10), pady=4)
        return bar, lbl

    def _style_ax(self, ax, ylabel: str):
        ax.set_facecolor("#2b2b2b")
        ax.set_xlim(0, MAX_POINTS)
        ax.set_ylim(0, 100)
        ax.set_ylabel(ylabel, color="#aaaaaa", fontsize=8)
        ax.tick_params(colors="#aaaaaa", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#444444")

    def update(self, stats: SystemStats) -> None:
        self._cpu_history.append(stats.cpu_percent)
        self._mem_history.append(stats.mem_percent)

        self._cpu_bar.set(stats.cpu_percent / 100)
        self._cpu_lbl.configure(text=f"{stats.cpu_percent:.0f}%")

        self._mem_bar.set(stats.mem_percent / 100)
        self._mem_lbl.configure(text=f"{stats.mem_percent:.0f}%")

        if stats.battery_percent is not None:
            self._bat_bar.set(stats.battery_percent / 100)
            self._bat_lbl.configure(text=f"{stats.battery_percent:.0f}%")
            status = "Charging" if stats.battery_charging else "Discharging"
            remain = f" · {stats.battery_remaining_min}min left" if stats.battery_remaining_min is not None else ""
            self._lbl_bat_detail.configure(text=f"Battery {status}{remain}")
        else:
            self._bat_bar.set(0)
            self._bat_lbl.configure(text="N/A")
            self._lbl_bat_detail.configure(text="")

        self._line_cpu.set_ydata(list(self._cpu_history))
        self._line_mem.set_ydata(list(self._mem_history))
        self._canvas.draw_idle()

        temp_str = f"온도: {stats.cpu_temp:.0f}°C" if stats.cpu_temp is not None else "온도: N/A"
        self._lbl_temp.configure(text=temp_str)
        self._lbl_disk.configure(
            text=f"디스크  R:{stats.disk_read_mbps:.1f}  W:{stats.disk_write_mbps:.1f} MB/s"
        )
        self._lbl_net.configure(
            text=f"↑{stats.net_up_mbps:.2f}  ↓{stats.net_down_mbps:.2f} MB/s"
        )
