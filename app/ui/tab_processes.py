import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from app.core.killer import is_protected, kill_process
from app.models.system_stats import ProcessInfo


class ProcessesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._all_processes: list[ProcessInfo] = []
        self._sort_attr = "cpu_percent"
        self._sort_reverse = True
        self._node_only = tk.BooleanVar(value=False)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_table())
        self._build_ui()

    def _build_ui(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkEntry(toolbar, textvariable=self._search_var,
                     placeholder_text="검색...", width=200).pack(side="left")
        ctk.CTkCheckBox(toolbar, text="Node.js만 보기",
                        variable=self._node_only, command=self._refresh_table).pack(side="left", padx=12)

        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="#eeeeee",
                        fieldbackground="#2b2b2b", rowheight=24, font=("Consolas", 9))
        style.configure("Treeview.Heading", background="#3b3b3b", foreground="#cccccc",
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1f538d")])

        cols = ("name", "pid", "cpu", "mem", "cmd")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        col_defs = [
            ("name", "NAME", 130),
            ("pid", "PID", 65),
            ("cpu", "CPU%", 65),
            ("mem", "MEM(MB)", 85),
            ("cmd", "COMMAND", 400),
        ]
        for col_id, label, width in col_defs:
            self._tree.heading(col_id, text=label, command=lambda c=col_id: self._sort_by(c))
            self._tree.column(col_id, width=width, minwidth=40, stretch=(col_id == "cmd"))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.tag_configure("node", foreground="#4fc3f7")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Delete>", lambda _: self._kill_selected())

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(5, 10))
        self._lbl_cmd = ctk.CTkLabel(bottom, text="", anchor="w", wraplength=680)
        self._lbl_cmd.pack(side="left", fill="x", expand=True)
        self._btn_kill = ctk.CTkButton(
            bottom, text="강제 종료", width=100,
            fg_color="#c0392b", hover_color="#922b21",
            command=self._kill_selected, state="disabled",
        )
        self._btn_kill.pack(side="right")

    def update(self, processes: list[ProcessInfo]):
        self._all_processes = processes
        self._refresh_table()

    def _filtered(self) -> list[ProcessInfo]:
        search = self._search_var.get().lower()
        result = self._all_processes
        if self._node_only.get():
            result = [p for p in result if "node" in p.name.lower()]
        if search:
            result = [p for p in result if search in p.name.lower() or search in p.cmdline.lower()]
        return sorted(result, key=lambda p: getattr(p, self._sort_attr), reverse=self._sort_reverse)

    def _refresh_table(self):
        selected_pid = self._selected_pid()
        self._tree.delete(*self._tree.get_children())
        for proc in self._filtered():
            tag = "node" if "node" in proc.name.lower() else ""
            self._tree.insert("", "end", iid=str(proc.pid), tags=(tag,), values=(
                proc.name,
                proc.pid,
                f"{proc.cpu_percent:.1f}",
                f"{proc.mem_mb:.1f}",
                proc.cmdline[:100],
            ))
        if selected_pid and self._tree.exists(str(selected_pid)):
            self._tree.selection_set(str(selected_pid))

    def _selected_pid(self) -> int | None:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self, _event=None):
        pid = self._selected_pid()
        if pid is None:
            self._lbl_cmd.configure(text="")
            self._btn_kill.configure(state="disabled")
            return
        proc = next((p for p in self._all_processes if p.pid == pid), None)
        if proc:
            self._lbl_cmd.configure(text=proc.cmdline)
            protected = is_protected(proc.name)
            self._btn_kill.configure(state="disabled" if protected else "normal")

    def _kill_selected(self):
        pid = self._selected_pid()
        if pid is None:
            return
        proc = next((p for p in self._all_processes if p.pid == pid), None)
        name = proc.name if proc else f"PID {pid}"
        if not messagebox.askyesno("강제 종료 확인", f"'{name}' (PID {pid})을(를) 강제 종료하시겠습니까?"):
            return
        ok, msg = kill_process(pid)
        if ok:
            self._tree.delete(str(pid))
            self._lbl_cmd.configure(text="")
            self._btn_kill.configure(state="disabled")
        else:
            messagebox.showerror("종료 실패", msg)

    def _sort_by(self, col: str):
        attr_map = {
            "name": "name", "pid": "pid",
            "cpu": "cpu_percent", "mem": "mem_mb", "cmd": "cmdline",
        }
        attr = attr_map[col]
        if self._sort_attr == attr:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_attr = attr
            self._sort_reverse = attr in ("cpu_percent", "mem_mb")
        self._refresh_table()
