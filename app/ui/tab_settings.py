from typing import Callable
import customtkinter as ctk
from app.core.settings import AppSettings

INTERVALS = [1, 2, 5, 10, 30, 60]


class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, settings: AppSettings, on_change: Callable[[AppSettings], None]):
        super().__init__(parent, fg_color="transparent")
        self._on_change = on_change
        self._interval_var = ctk.IntVar(value=settings.refresh_interval)
        self._theme_var = ctk.StringVar(value=settings.theme)
        self._start_tab_var = ctk.StringVar(value=settings.start_tab)
        self._build_ui()

    def _build_ui(self):
        section_font = ctk.CTkFont(size=13, weight="bold")
        pad = {"padx": 24, "pady": (16, 6)}

        ctk.CTkLabel(self, text="갱신 주기", font=section_font).pack(anchor="w", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=24, pady=(0, 8))
        for val in INTERVALS:
            ctk.CTkRadioButton(
                row, text=f"{val}초", variable=self._interval_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

        ctk.CTkLabel(self, text="테마", font=section_font).pack(anchor="w", **pad)
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(anchor="w", padx=24, pady=(0, 8))
        for val, label in [("dark", "Dark"), ("light", "Light")]:
            ctk.CTkRadioButton(
                row2, text=label, variable=self._theme_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

        ctk.CTkLabel(self, text="시작 탭", font=section_font).pack(anchor="w", **pad)
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(anchor="w", padx=24, pady=(0, 8))
        for val, label in [("overview", "Overview"), ("processes", "Processes")]:
            ctk.CTkRadioButton(
                row3, text=label, variable=self._start_tab_var,
                value=val, command=self._save,
            ).pack(side="left", padx=8)

    def _save(self):
        self._on_change(AppSettings(
            refresh_interval=self._interval_var.get(),
            theme=self._theme_var.get(),
            start_tab=self._start_tab_var.get(),
        ))
