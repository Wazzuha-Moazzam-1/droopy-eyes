"""Simple desktop frontend for the detection controller.

Run from the project directory with:
    python "Controller/frontend/front end.py"
"""

from __future__ import annotations

import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, VERTICAL, X, Y, StringVar, Tk, messagebox
from tkinter import ttk


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from frontend.api import DetectionAPI


class DetectionFrontend:
    """Tkinter frontend that owns blacklist settings and monitoring state."""

    COLORS = {
        "background": "#fff1f7",
        "surface": "#fffafd",
        "navy": "#54213d",
        "muted": "#8f6078",
        "blue": "#d94686",
        "green": "#b83270",
        "red": "#c93636",
        "border": "#f2bfd5",
    }

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Focus Guard")
        self.root.geometry("980x650")
        self.root.minsize(820, 560)
        self.root.configure(bg=self.COLORS["background"])

        self.api = DetectionAPI()
        self.app_blacklist = self.api.get_blacklist("app")
        self.website_blacklist = self.api.get_blacklist("website")
        self.app_monitor_enabled = False
        self.tab_monitor_enabled = False
        self.monitoring = False
        self.monitor_thread: threading.Thread | None = None
        self.stop_monitor = threading.Event()
        self.detection_process: subprocess.Popen[str] | None = None

        self.status_text = StringVar(value="Monitoring is stopped")
        self.app_count = StringVar(value="0 apps")
        self.website_count = StringVar(value="0 websites")
        self.last_event = StringVar(value="No activity recorded yet")
        self._configure_style()
        self._build_layout()
        self._refresh_lists()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["background"])
        style.configure("Surface.TFrame", background=self.COLORS["surface"])
        style.configure("TLabel", background=self.COLORS["background"], foreground=self.COLORS["navy"])
        style.configure("Muted.TLabel", foreground=self.COLORS["muted"])
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground=self.COLORS["navy"])
        style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"), foreground=self.COLORS["navy"])
        style.configure("Card.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["navy"])
        style.configure("CardMuted.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["muted"])
        style.configure("Accent.TButton", background=self.COLORS["blue"], foreground="white", padding=(14, 8))
        style.map("Accent.TButton", background=[("active", "#be326f")])
        style.configure("TNotebook", background=self.COLORS["background"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 9))
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(28, 22, 28, 12))
        header.pack(fill=X)
        ttk.Label(header, text="Focus Guard", style="Title.TLabel").pack(side=LEFT)
        ttk.Label(
            header,
            text="Detection and distraction control",
            style="Muted.TLabel",
        ).pack(side=LEFT, padx=(14, 0), pady=(9, 0))
        ttk.Label(header, textvariable=self.status_text, style="Muted.TLabel").pack(
            side=RIGHT, pady=(9, 0)
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        self.dashboard_tab = ttk.Frame(self.notebook, padding=22)
        self.blacklist_tab = ttk.Frame(self.notebook, padding=22)
        self.settings_tab = ttk.Frame(self.notebook, padding=22)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.blacklist_tab, text="Blacklist")
        self.notebook.add(self.settings_tab, text="Settings")
        self._build_dashboard()
        self._build_blacklist()
        self._build_settings()

    def _card(self, parent: ttk.Frame, title: str, value: StringVar, subtitle: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Surface.TFrame", padding=18)
        card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))
        ttk.Label(card, text=title, style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=value, style="Card.TLabel", font=("Segoe UI", 21, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        ttk.Label(card, text=subtitle, style="CardMuted.TLabel").pack(anchor="w")
        return card

    def _build_dashboard(self) -> None:
        ttk.Label(self.dashboard_tab, text="Overview", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.dashboard_tab,
            text="Choose what Focus Guard should watch, then start monitoring.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill=X)
        self._card(cards, "Blocked apps", self.app_count, "saved in your blacklist")
        self._card(cards, "Blocked websites", self.website_count, "checked by the tab monitor")
        self._card(cards, "Last event", self.last_event, "most recent monitor update")

        controls = ttk.Frame(self.dashboard_tab, style="Surface.TFrame", padding=18)
        controls.pack(fill=X, pady=24)
        ttk.Label(controls, text="Monitoring", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            controls,
            text="The app monitor checks running processes. The tab monitor is configured by the browser extension.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(4, 14))
        ttk.Button(
            controls,
            text="Start monitoring",
            style="Accent.TButton",
            command=self._toggle_monitoring,
        ).pack(side=LEFT)
        ttk.Button(
            controls,
            text="Manage blacklist",
            command=lambda: self.notebook.select(self.blacklist_tab),
        ).pack(side=LEFT, padx=10)
        self.monitor_button = controls.winfo_children()[-2]

        activity = ttk.Frame(self.dashboard_tab, style="Surface.TFrame", padding=18)
        activity.pack(fill=BOTH, expand=True)
        ttk.Label(activity, text="Activity", style="Heading.TLabel").pack(anchor="w")
        self.activity_list = ttk.Treeview(activity, columns=("time", "event"), show="headings")
        self.activity_list.heading("time", text="Time")
        self.activity_list.heading("event", text="Event")
        self.activity_list.column("time", width=110, stretch=False)
        self.activity_list.column("event", width=600)
        self.activity_list.pack(side=LEFT, fill=BOTH, expand=True, pady=(12, 0))
        scrollbar = ttk.Scrollbar(activity, orient=VERTICAL, command=self.activity_list.yview)
        scrollbar.pack(side=RIGHT, fill=Y, pady=(12, 0))
        self.activity_list.configure(yscrollcommand=scrollbar.set)

    def _build_blacklist(self) -> None:
        ttk.Label(self.blacklist_tab, text="Blacklist", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.blacklist_tab,
            text="Add app names such as spotify.exe or website domains such as youtube.com.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        columns = ttk.Frame(self.blacklist_tab)
        columns.pack(fill=BOTH, expand=True)
        self._build_blacklist_column(columns, "Apps", "app")
        self._build_blacklist_column(columns, "Websites", "website")

    def _build_blacklist_column(self, parent: ttk.Frame, title: str, kind: str) -> None:
        frame = ttk.Frame(parent, style="Surface.TFrame", padding=16)
        frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12 if kind == "app" else 0))
        ttk.Label(frame, text=title, style="Heading.TLabel").pack(anchor="w")
        entry = ttk.Entry(frame)
        entry.pack(fill=X, pady=(12, 8))
        entry.bind("<Return>", lambda _event: self._add_entry(kind, entry))
        setattr(self, f"{kind}_entry", entry)
        ttk.Button(frame, text=f"Add {kind}", style="Accent.TButton", command=lambda: self._add_entry(kind, entry)).pack(
            anchor="w"
        )
        tree = ttk.Treeview(frame, columns=("value",), show="headings", selectmode="extended")
        tree.heading("value", text="Blocked name")
        tree.column("value", width=310)
        tree.pack(fill=BOTH, expand=True, pady=(16, 8))
        setattr(self, f"{kind}_list", tree)
        delete_label = "Remove selected app(s)" if kind == "app" else "Remove selected website(s)"
        delete_button = ttk.Button(
            frame,
            text=delete_label,
            command=lambda: self._remove_selected(kind, tree),
        )
        delete_button.pack(anchor="w")
        tree.bind("<Delete>", lambda _event: self._remove_selected(kind, tree))

    def _build_settings(self) -> None:
        ttk.Label(self.settings_tab, text="Monitor settings", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.settings_tab,
            text="Enable only the monitors you want to use during a focus session.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 18))
        self.app_enabled_var = StringVar(value="off")
        self.tab_enabled_var = StringVar(value="off")
        self._setting_row(
            self.settings_tab,
            "Application monitor",
            "Detects and closes blacklisted running processes on this computer.",
            self.app_enabled_var,
            "app",
        )
        self._setting_row(
            self.settings_tab,
            "Browser tab monitor",
            "Uses the browser extension to identify blacklisted websites.",
            self.tab_enabled_var,
            "tab",
        )

    def _setting_row(
        self, parent: ttk.Frame, title: str, description: str, variable: StringVar, kind: str
    ) -> None:
        row = ttk.Frame(parent, style="Surface.TFrame", padding=16)
        row.pack(fill=X, pady=(0, 12))
        ttk.Label(row, text=title, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(row, text=description, style="CardMuted.TLabel").pack(anchor="w", pady=(3, 10))
        ttk.Checkbutton(
            row,
            text="Enabled",
            variable=variable,
            onvalue="on",
            offvalue="off",
            command=lambda: self._setting_changed(kind, variable.get() == "on"),
        ).pack(anchor="w")

    def _refresh_lists(self) -> None:
        for kind, values in (("app", self.app_blacklist), ("website", self.website_blacklist)):
            tree: ttk.Treeview = getattr(self, f"{kind}_list")
            tree.delete(*tree.get_children())
            for value in values:
                tree.insert("", END, values=(value,))
        self.app_count.set(f"{len(self.app_blacklist)} apps")
        self.website_count.set(f"{len(self.website_blacklist)} websites")

    def _add_entry(self, kind: str, entry: ttk.Entry) -> None:
        value = entry.get().strip()
        if not value:
            messagebox.showwarning("Missing value", f"Enter an {kind} name first.", parent=self.root)
            return
        values: list[str] = getattr(self, f"{kind}_blacklist")
        if any(item.casefold() == value.casefold() for item in values):
            messagebox.showinfo("Already added", "That item is already on the blacklist.", parent=self.root)
            return
        values[:] = self.api.add_blacklist_item(kind, value)
        entry.delete(0, END)
        self._refresh_lists()
        self._record_event(f"Added {kind}: {value}")

    def _remove_selected(self, kind: str, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo(
                "Nothing selected",
                "Click an item in the list first, then choose Remove selected.",
                parent=self.root,
            )
            return
        values_to_remove = {tree.item(item, "values")[0] for item in selected}
        item_word = "app" if kind == "app" else "website"
        if not messagebox.askyesno(
            f"Remove {item_word}",
            f"Remove {', '.join(sorted(values_to_remove))} from the blacklist?",
            parent=self.root,
        ):
            return
        try:
            values: list[str] = getattr(self, f"{kind}_blacklist")
            values[:] = self.api.delete_blacklist_items(kind, values_to_remove)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not update blacklist", str(error), parent=self.root)
            return
        self._refresh_lists()
        self._record_event(f"Removed {len(values_to_remove)} {item_word} blacklist item(s)")

    def _setting_changed(self, kind: str, enabled: bool) -> None:
        if kind == "app":
            self.app_monitor_enabled = enabled
        else:
            self.tab_monitor_enabled = enabled
        self._record_event(f"{kind.title()} monitor {'enabled' if enabled else 'disabled'}")

    def _toggle_monitoring(self) -> None:
        self.monitoring = not self.monitoring
        if self.monitoring:
            self.stop_monitor.clear()
            self.monitor_button.configure(text="Stop monitoring")
            self.status_text.set("Monitoring is active")
            self._record_event("Monitoring started")
            if not self._start_detection_controller():
                self.monitoring = False
                self.stop_monitor.set()
                self.monitor_button.configure(text="Start monitoring")
                self.status_text.set("Monitoring is stopped")
                return
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.stop_monitor.set()
            self._stop_detection_controller()
            self.monitor_button.configure(text="Start monitoring")
            self.status_text.set("Monitoring is stopped")
            self._record_event("Monitoring stopped")

    def _start_detection_controller(self) -> bool:
        if self.detection_process is not None and self.detection_process.poll() is None:
            return True

        project_python = PROJECT_DIR.parent / ".venv" / "Scripts" / "python.exe"
        python_executable = (
            str(project_python) if project_python.exists() else sys.executable
        )
        try:
            self.detection_process = subprocess.Popen(
                [python_executable, "-m", "Controller.main"],
                cwd=PROJECT_DIR.parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            self._record_event(f"Could not start detection controller: {error}")
            return False

        threading.Thread(
            target=self._read_detection_errors,
            args=(self.detection_process,),
            daemon=True,
        ).start()
        self._record_event("Webcam detection controller started")
        return True

    def _read_detection_errors(self, process: subprocess.Popen[str]) -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            message = line.strip()
            if message:
                self.root.after(
                    0,
                    lambda error_message=message: self._record_event(
                        f"Detection controller: {error_message}"
                    ),
                )

    def _stop_detection_controller(self) -> None:
        process = self.detection_process
        self.detection_process = None
        if process is None or process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        self._record_event("Webcam detection controller stopped")

    def _monitor_loop(self) -> None:
        previous: set[str] = set()
        while not self.stop_monitor.wait(2):
            if (
                self.detection_process is not None
                and self.detection_process.poll() is not None
            ):
                exit_code = self.detection_process.returncode
                self.root.after(
                    0,
                    lambda code=exit_code: self._record_event(
                        f"Webcam detection controller stopped (exit code {code})"
                    ),
                )
                self.detection_process = None
            if not self.app_monitor_enabled:
                continue
            try:
                current = self.api.find_running_blacklisted_apps()
            except RuntimeError as error:
                self.root.after(0, lambda message=str(error): self._record_event(message))
                return
            newly_detected = current - previous
            if newly_detected:
                try:
                    closed, failures = self.api.close_running_blacklisted_apps(newly_detected)
                except RuntimeError as error:
                    self.root.after(0, lambda message=str(error): self._record_event(message))
                    return
                for app in closed:
                    self.root.after(
                        0,
                        lambda item=app: self._record_event(
                            f"{item['method'].title()} blacklisted app: {item['name']}"
                        ),
                    )
                for failure in failures:
                    self.root.after(
                        0,
                        lambda item=failure: self._record_event(
                            f"Could not close {item['name']}: {item['reason']}"
                        ),
                    )
            previous = current

    def _record_event(self, event: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_event.set(event)
        if hasattr(self, "activity_list"):
            self.activity_list.insert("", 0, values=(timestamp, event))

    def _close(self) -> None:
        self.stop_monitor.set()
        self._stop_detection_controller()
        self.root.destroy()


def main() -> None:
    root = Tk()
    DetectionFrontend(root)
    root.mainloop()


if __name__ == "__main__":
    main()