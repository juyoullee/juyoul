import math
import os
import random
import sys
import threading
import time
import traceback
import tkinter as tk
from copy import deepcopy
from datetime import datetime
from tkinter import messagebox, ttk

import keyboard
import pyautogui
import schedule

from Core.action_specs import ActionSpec, BoardSpec, ScheduleSpec
from Core.custom_actions import RecordedActionLibrary
from Core.window_control import bring_to_front, count_windows, has_window, list_windows, minimize_window
from games.actions.Carbal import CarbalRed
from games.actions.L2m import L2mDayDungeonAction, L2mDayilyAction
from games.actions.Odin import Odin_Action

sys.dont_write_bytecode = True

APP_TITLE = "ControlCentor"
APP_SIZE = "1260x860"
LOG_PATH = os.path.join(os.path.dirname(__file__), "controlcentor.log")
CUSTOM_ACTIONS_PATH = os.path.join(os.path.dirname(__file__), "custom_actions.json")
ACTION_COOLDOWN_SECONDS = 10
ACTION_TIMEOUT_SECONDS = 600

BOARD_OPTIONS = [
    ("odin", "ODIN"),
    ("l2m", "Lineage2M"),
    ("carbal", "CARBAL"),
    ("l2m_dungeon", "L2M Dungeon"),
    ("l2m_custom", "L2M Custom"),
]
BOARD_LABELS = {board_id: label for board_id, label in BOARD_OPTIONS}
WINDOW_LAYOUT_OPTIONS = [
    ("l2m_9_grid", "L2M 9창 3x3"),
]
EXPECTED_WINDOW_COUNTS = {
    "Lineage2M": 9,
}


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as file:
            file.write(line + "\n")
    except Exception:
        pass


def log_exc(prefix="EXCEPTION"):
    log(prefix + "\n" + traceback.format_exc())


def safe_focus(title):
    if not title:
        return

    try:
        bring_to_front(title)
    except Exception as exc:
        log(f"FOCUS FAILED {title} / {exc}")


def safe_minimize(title):
    if not title:
        return

    try:
        minimize_window(title)
    except Exception as exc:
        log(f"MINIMIZE FAILED {title} / {exc}")


def validate_target_windows(title):
    if not title:
        return True, ""

    windows = list_windows(title)
    if not windows:
        return False, f"대상 창이 없습니다: {title}"

    expected = EXPECTED_WINDOW_COUNTS.get(title)
    if expected is not None and len(windows) < expected:
        return False, f"{title} 창이 {len(windows)}개만 감지되었습니다. 예상 개수: {expected}"

    visible_count = sum(1 for item in windows if item["visible"])
    if visible_count == 0:
        return False, f"감지된 {title} 창이 모두 비가시 상태입니다."

    return True, f"{title} 창 {len(windows)}개 감지"


def pick_time(hour, start_min, end_min):
    now = datetime.now()

    if now.hour < hour:
        return f"{hour:02d}:{random.randint(start_min, end_min):02d}"

    if now.hour == hour:
        start = max(start_min, now.minute + 1)
        if start <= end_min:
            return f"{hour:02d}:{random.randint(start, end_min):02d}"

    return f"{hour:02d}:{random.randint(start_min, end_min):02d}"


class AutoButtonGrid:

    def __init__(self, parent, on_click, columns=4):
        self.parent = parent
        self.on_click = on_click
        self.columns = columns

        for col in range(columns):
            parent.columnconfigure(col, weight=1)

    def render(self, actions):
        if not actions:
            placeholder = tk.Label(
                self.parent,
                text="등록된 동작이 없습니다.",
                bg=self.parent.cget("bg"),
                fg="#7f8a9a",
                font=("Malgun Gothic", 10),
                anchor="w",
            )
            placeholder.grid(row=0, column=0, sticky="w")
            return

        for index, spec in enumerate(actions):
            row, col = divmod(index, self.columns)
            button = ttk.Button(
                self.parent,
                text=spec.label,
                style="Board.TButton",
                command=lambda current=spec: self.on_click(current),
            )

            if not spec.enabled:
                button.state(["disabled"])

            button.grid(row=row, column=col, padx=6, pady=6, sticky="ew")


class ControlCenterApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(APP_SIZE)
        self.root.configure(bg="#0b1220")

        self.schedule_items = {}
        self.last_day = datetime.now().day
        self.board_frames = {}
        self.content_frame = None
        self.board_canvas = None
        self.board_scrollbar = None
        self.board_container = None
        self.safety_label = None
        self.emergency_stop = False
        self.last_run_at = 0.0
        self.active_action_count = 0
        self.guard_lock = threading.Lock()

        self.providers = self._build_providers()
        self.board_specs = self._build_board_specs()
        self.schedule_specs = self._build_schedule_specs()
        self.action_specs = self._collect_actions()
        self.actions_by_id = {spec.id: spec for spec in self.action_specs}

        self._configure_style()
        self._build_layout()
        self._render_boards()
        self._set_today_schedule()

        self.root.after(1000, self._scheduler_tick)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_providers(self):
        return [
            Odin_Action(),
            L2mDayilyAction(),
            CarbalRed(),
            L2mDayDungeonAction(),
            RecordedActionLibrary(
                CUSTOM_ACTIONS_PATH,
                self.open_macro_creator,
                self.open_macro_manager,
            ),
        ]

    def _build_board_specs(self):
        return [
            BoardSpec(id="odin", title="ODIN", columns=3),
            BoardSpec(id="l2m", title="Lineage2M", columns=3),
            BoardSpec(id="carbal", title="CARBAL", columns=3),
            BoardSpec(id="l2m_dungeon", title="L2M Dungeon", columns=2),
            BoardSpec(id="l2m_custom", title="Macro Studio", columns=2),
        ]

    def _build_schedule_specs(self):
        return [
            ScheduleSpec(
                id="schedule.carbal.daily",
                label="카르발 데일리",
                time_picker=lambda: pick_time(5, 0, 30),
                runner=lambda: self._request_run_by_id("carbal.daily"),
            ),
        ]

    def _collect_actions(self):
        actions = []

        for provider in self.providers:
            getter = getattr(provider, "get_action_specs", None)
            if getter is None:
                continue
            actions.extend(getter())

        return actions

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Board.TButton",
            font=("Malgun Gothic", 10, "bold"),
            padding=(10, 8),
            foreground="#e8edf7",
            background="#1f2a3a",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Board.TButton",
            background=[("active", "#30415c"), ("pressed", "#3a4d6c")],
        )

        style.configure(
            "Primary.TButton",
            font=("Malgun Gothic", 10, "bold"),
            padding=(12, 8),
            foreground="#f7fbff",
            background="#2563eb",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
        )

        style.configure(
            "Danger.TButton",
            font=("Malgun Gothic", 10, "bold"),
            padding=(12, 8),
            foreground="#fff7f7",
            background="#b91c1c",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#991b1b"), ("pressed", "#7f1d1d")],
        )

        style.configure("Panel.TCombobox", padding=6)

    def _build_layout(self):
        shell = tk.Frame(self.root, bg="#0b1220")
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        self.schedule_label = None
        self.health_label = None
        self.safety_label = None

        top_bar = tk.Frame(shell, bg="#0b1220")
        top_bar.pack(fill="x", pady=(0, 10))

        left = tk.Frame(top_bar, bg="#0b1220")
        left.pack(side="left", fill="x", expand=True)

        self.schedule_label = tk.Label(
            left,
            text="schedule: -",
            bg="#0b1220",
            fg="#8da2c0",
            font=("Malgun Gothic", 9),
            anchor="w",
        )
        self.schedule_label.pack(fill="x")

        self.health_label = tk.Label(
            left,
            text="health: -",
            bg="#0b1220",
            fg="#8da2c0",
            font=("Malgun Gothic", 9),
            anchor="w",
        )
        self.health_label.pack(fill="x", pady=(2, 0))

        right = tk.Frame(top_bar, bg="#0b1220")
        right.pack(side="right")

        self.safety_label = tk.Label(
            right,
            text=f"cooldown {ACTION_COOLDOWN_SECONDS}s | timeout {ACTION_TIMEOUT_SECONDS}s",
            bg="#0b1220",
            fg="#93c5fd",
            font=("Malgun Gothic", 9, "bold"),
        )
        self.safety_label.pack(side="left", padx=(0, 8))

        ttk.Button(right, text="긴급 정지", style="Danger.TButton", command=self._activate_emergency_stop).pack(side="left")
        ttk.Button(right, text="정지 해제", style="Board.TButton", command=self._release_emergency_stop).pack(side="left", padx=(8, 0))

        content_shell = tk.Frame(shell, bg="#0b1220")
        content_shell.pack(fill="both", expand=True)

        self.board_canvas = tk.Canvas(
            content_shell,
            bg="#0b1220",
            highlightthickness=0,
            bd=0,
        )
        self.board_canvas.pack(side="left", fill="both", expand=True)

        self.board_scrollbar = ttk.Scrollbar(
            content_shell,
            orient="vertical",
            command=self.board_canvas.yview,
        )
        self.board_scrollbar.pack(side="right", fill="y")
        self.board_canvas.configure(yscrollcommand=self.board_scrollbar.set)

        self.content_frame = tk.Frame(self.board_canvas, bg="#0b1220")
        self.board_container = self.board_canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor="nw",
        )

        self.content_frame.bind("<Configure>", self._sync_board_scrollregion)
        self.board_canvas.bind("<Configure>", self._resize_board_container)
        self.board_canvas.bind_all("<MouseWheel>", self._on_board_mousewheel)

    def _sync_board_scrollregion(self, event=None):
        if self.board_canvas is None:
            return
        self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))

    def _resize_board_container(self, event):
        if self.board_canvas is None or self.board_container is None:
            return
        self.board_canvas.itemconfigure(self.board_container, width=event.width)

    def _on_board_mousewheel(self, event):
        if self.board_canvas is None:
            return
        delta = int(-1 * (event.delta / 120))
        if delta != 0:
            self.board_canvas.yview_scroll(delta, "units")

    def _render_boards(self):
        for child in self.content_frame.winfo_children():
            child.destroy()

        self.board_frames.clear()

        columns = 2
        rows = max(1, math.ceil(len(self.board_specs) / columns))

        for col in range(columns):
            self.content_frame.columnconfigure(col, weight=1, uniform="boards")
        for row in range(rows):
            self.content_frame.rowconfigure(row, weight=1)

        for index, board in enumerate(self.board_specs):
            row, col = divmod(index, columns)
            outer = tk.Frame(
                self.content_frame,
                bg="#ffffff",
                highlightbackground="#d8e0ec",
                highlightthickness=1,
            )
            outer.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            title_row = tk.Frame(outer, bg="#ffffff")
            title_row.pack(fill="x", padx=14, pady=(14, 8))

            title = tk.Label(
                title_row,
                text=board.title,
                bg="#ffffff",
                fg="#142033",
                font=("Malgun Gothic", 12, "bold"),
            )
            title.pack(side="left")

            count = sum(1 for spec in self.action_specs if spec.board == board.id)
            badge = tk.Label(
                title_row,
                text=f"{count} actions",
                bg="#edf4ff",
                fg="#2450b8",
                font=("Malgun Gothic", 9, "bold"),
                padx=8,
                pady=2,
            )
            badge.pack(side="right")

            separator = tk.Frame(outer, bg="#edf1f6", height=1)
            separator.pack(fill="x", padx=14)

            inner = tk.Frame(outer, bg="#ffffff")
            inner.pack(fill="both", expand=True, padx=12, pady=12)
            self.board_frames[board.id] = inner

            actions = [spec for spec in self.action_specs if spec.board == board.id]
            AutoButtonGrid(inner, on_click=self.request_run, columns=board.columns).render(actions)

        self.content_frame.update_idletasks()
        self._sync_board_scrollregion()

    def request_run(self, spec: ActionSpec):
        self.root.after(0, lambda: self._show_countdown_and_run(spec))

    def _request_run_by_id(self, action_id):
        spec = self.actions_by_id.get(action_id)
        if spec is None:
            log(f"MISSING ACTION {action_id}")
            return
        self.request_run(spec)

    def _preflight_action(self, spec: ActionSpec):
        if not spec.pre_focus:
            return True

        ok, message = validate_target_windows(spec.pre_focus)
        if not ok:
            log(f"PRECHECK FAILED {spec.id} / {message}")
            messagebox.showwarning("실행 중단", message, parent=self.root)
            self._restore_gui()
            return False

        log(f"PRECHECK OK {spec.id} / {message}")
        return True

    def _show_countdown_and_run(self, spec: ActionSpec):
        if self.emergency_stop:
            messagebox.showwarning("실행 차단", "긴급 정지 상태입니다. 정지 해제 후 실행하세요.", parent=self.root)
            return

        countdown = max(0, spec.countdown)
        if countdown == 0:
            self._start_action(spec)
            return

        popup = tk.Toplevel(self.root)
        popup.title("실행 준비")
        popup.geometry("260x160")
        popup.configure(bg="#ffffff")
        popup.attributes("-topmost", True)

        tk.Label(
            popup,
            text=spec.label,
            bg="#ffffff",
            fg="#142033",
            font=("Malgun Gothic", 11, "bold"),
        ).pack(pady=(18, 6))

        label = tk.Label(
            popup,
            text=str(countdown),
            bg="#ffffff",
            fg="#2563eb",
            font=("Malgun Gothic", 30, "bold"),
        )
        label.pack(expand=True)

        def tick(value):
            if value == 0:
                popup.destroy()
                self._start_action(spec)
                return

            label.config(text=str(value))
            popup.after(1000, tick, value - 1)

        tick(countdown)

    def _run_action_task(self, spec: ActionSpec):
        try:
            log(f"START {spec.id} / {spec.label}")

            if spec.pre_focus:
                safe_focus(spec.pre_focus)

            if spec.background:
                result = self._run_with_timeout(spec)
            else:
                result = spec.runner()
            if result is False:
                log(f"STOPPED {spec.id} / {spec.label}")
            else:
                log(f"DONE {spec.id} / {spec.label}")
        except Exception:
            log_exc(spec.id)
        finally:
            with self.guard_lock:
                self.active_action_count = max(0, self.active_action_count - 1)

            if spec.post_minimize:
                safe_minimize(spec.post_minimize)

            self.root.after(500, self._restore_gui)

    def _start_action(self, spec: ActionSpec):
        with self.guard_lock:
            now = time.time()
            if self.active_action_count > 0:
                messagebox.showwarning("실행 대기", "이미 다른 동작이 실행 중입니다.", parent=self.root)
                return
            if now - self.last_run_at < ACTION_COOLDOWN_SECONDS:
                remaining = max(0, int(ACTION_COOLDOWN_SECONDS - (now - self.last_run_at)))
                messagebox.showwarning("쿨다운", f"다음 실행까지 {remaining}초 기다려주세요.", parent=self.root)
                return
            self.active_action_count += 1
            self.last_run_at = now

        if spec.minimize_gui:
            try:
                self.root.iconify()
            except Exception:
                pass

        if spec.background:
            threading.Thread(target=lambda: self._run_action_task(spec), daemon=True).start()
        else:
            self._run_action_task(spec)

    def _restore_gui(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def _run_with_timeout(self, spec: ActionSpec):
        holder = {"result": None, "error": None}

        def worker():
            try:
                holder["result"] = spec.runner()
            except Exception as exc:
                holder["error"] = exc

        runner_thread = threading.Thread(target=worker, daemon=True)
        runner_thread.start()
        runner_thread.join(ACTION_TIMEOUT_SECONDS)

        if runner_thread.is_alive():
            self._stop_all_running_actions()
            log(f"TIMEOUT {spec.id} / {spec.label} / {ACTION_TIMEOUT_SECONDS}s")
            return False

        if holder["error"] is not None:
            raise holder["error"]

        return holder["result"]

    def _stop_all_running_actions(self):
        for provider in self.providers:
            if hasattr(provider, "RUNNING"):
                provider.RUNNING = False

    def _activate_emergency_stop(self):
        self.emergency_stop = True
        self._stop_all_running_actions()
        if self.safety_label is not None:
            self.safety_label.config(text="EMERGENCY STOP ON", fg="#fca5a5")
        log("EMERGENCY STOP ON")

    def _release_emergency_stop(self):
        self.emergency_stop = False
        if self.safety_label is not None:
            self.safety_label.config(
                text=f"cooldown {ACTION_COOLDOWN_SECONDS}s | timeout {ACTION_TIMEOUT_SECONDS}s",
                fg="#93c5fd",
            )
        log("EMERGENCY STOP OFF")

    def _update_schedule_label(self):
        if self.schedule_label is None:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"{item['time']}  {item['label']}" for item in self.schedule_items.values()]

        if not lines:
            summary = "??? ?? ??"
        else:
            summary = " / ".join(lines[:2])
            if len(lines) > 2:
                summary += f" ? {len(lines) - 2}?"

        self.schedule_label.config(text=f"{today}  {summary}")

    def _update_health_label(self):
        if self.health_label is None:
            return

        lines = []

        for title, expected in EXPECTED_WINDOW_COUNTS.items():
            current = count_windows(title)
            status = "??" if current >= expected else "??"
            lines.append(f"{title}: {current}/{expected} ({status})")

        if not lines:
            lines = ["?? ? ?? ??"]

        self.health_label.config(text="  |  ".join(lines))
    def _refresh_actions(self):
        self.action_specs = self._collect_actions()
        self.actions_by_id = {spec.id: spec for spec in self.action_specs}
        self._render_boards()

    def _get_macro_provider(self):
        for provider in self.providers:
            if isinstance(provider, RecordedActionLibrary):
                return provider
        return None

    def open_macro_creator(self):
        provider = self._get_macro_provider()
        if provider is None:
            messagebox.showerror("오류", "사용자 매크로 저장소를 찾을 수 없습니다.", parent=self.root)
            return False

        dialog = tk.Toplevel(self.root)
        dialog.title("동작 추가")
        dialog.geometry("760x760")
        dialog.minsize(760, 760)
        dialog.configure(bg="#f4f7fb")
        dialog.attributes("-topmost", True)
        dialog.transient(self.root)
        dialog.grab_set()

        state = {
            "recording": False,
            "steps": [],
            "last_time": None,
            "drag_start": None,
        }

        name_var = tk.StringVar()
        board_var = tk.StringVar(value="L2M Custom")
        focus_var = tk.StringVar(value="Lineage2M")
        countdown_var = tk.StringVar(value="3")
        status_var = tk.StringVar(value="매크로 이름을 입력한 뒤 녹화를 시작하거나 수동 스텝을 추가하세요.")

        card = tk.Frame(dialog, bg="#ffffff", highlightbackground="#d8e0ec", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            card,
            text="Macro Builder",
            bg="#ffffff",
            fg="#142033",
            font=("Malgun Gothic", 16, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))

        tk.Label(
            card,
            text="녹화와 수동 입력을 섞어서 원하는 버튼 동작을 만들 수 있습니다.",
            bg="#ffffff",
            fg="#607086",
            font=("Malgun Gothic", 10),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        form = tk.Frame(card, bg="#ffffff")
        form.pack(fill="x", padx=16)

        self._build_labeled_entry(form, "버튼 이름", name_var, 0, 0)
        self._build_labeled_combo(form, "배치 위치", board_var, [label for _, label in BOARD_OPTIONS], 0, 1)
        self._build_labeled_entry(form, "대상 창 제목", focus_var, 1, 0)
        self._build_labeled_entry(form, "카운트다운", countdown_var, 1, 1)

        info_text = (
            "녹화 단축키\n"
            "F8: 클릭 기록\n"
            "F9: 드래그 시작점 기록\n"
            "F10: 드래그 종료점 기록\n"
            "ESC: 녹화 종료"
        )
        info_box = tk.Label(
            card,
            text=info_text,
            justify="left",
            bg="#eef4ff",
            fg="#24447a",
            font=("Malgun Gothic", 10),
            padx=12,
            pady=10,
        )
        info_box.pack(fill="x", padx=16, pady=(14, 8))

        tk.Label(
            card,
            textvariable=status_var,
            bg="#ffffff",
            fg="#166534",
            font=("Malgun Gothic", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        action_row = tk.Frame(card, bg="#ffffff")
        action_row.pack(fill="x", padx=16, pady=(0, 12))

        tabs = ttk.Notebook(card)
        tabs.pack(fill="x", padx=16, pady=(0, 12))

        manual_drag_tab = tk.Frame(tabs, bg="#ffffff")
        pattern_tab = tk.Frame(tabs, bg="#ffffff")
        window_tab = tk.Frame(tabs, bg="#ffffff")
        delay_tab = tk.Frame(tabs, bg="#ffffff")
        tabs.add(manual_drag_tab, text="드래그 입력")
        tabs.add(pattern_tab, text="반복 패턴")
        tabs.add(window_tab, text="창 반복")
        tabs.add(delay_tab, text="대기 추가")

        list_card = tk.Frame(card, bg="#f8fafc", highlightbackground="#d8e0ec", highlightthickness=1)
        list_card.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        tk.Label(
            list_card,
            text="스텝 목록",
            bg="#f8fafc",
            fg="#142033",
            font=("Malgun Gothic", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        listbox = tk.Listbox(
            list_card,
            height=8,
            font=("Consolas", 10),
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
        )
        listbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        drag_vars = {
            "start_x": tk.StringVar(),
            "start_y": tk.StringVar(),
            "delta_x": tk.StringVar(),
            "delta_y": tk.StringVar(),
            "duration": tk.StringVar(value="0.25"),
            "after": tk.StringVar(value="0.05"),
        }
        self._build_numeric_form(
            manual_drag_tab,
            [
                ("시작 X", "start_x"),
                ("시작 Y", "start_y"),
                ("Delta X", "delta_x"),
                ("Delta Y", "delta_y"),
                ("지속시간", "duration"),
                ("후 대기", "after"),
            ],
            drag_vars,
        )

        pattern_vars = {
            "start_x": tk.StringVar(),
            "start_y": tk.StringVar(),
            "delta_x": tk.StringVar(),
            "delta_y": tk.StringVar(),
            "count": tk.StringVar(value="3"),
            "after": tk.StringVar(value="0.08"),
        }
        self._build_numeric_form(
            pattern_tab,
            [
                ("시작 X", "start_x"),
                ("시작 Y", "start_y"),
                ("X 증가", "delta_x"),
                ("Y 증가", "delta_y"),
                ("횟수", "count"),
                ("클릭 후 대기", "after"),
            ],
            pattern_vars,
        )

        window_vars = {
            "layout": tk.StringVar(value="L2M 9창 3x3"),
            "mode": tk.StringVar(value="클릭"),
            "base_x": tk.StringVar(),
            "base_y": tk.StringVar(),
            "delta_x": tk.StringVar(value="0"),
            "delta_y": tk.StringVar(value="0"),
            "duration": tk.StringVar(value="0.25"),
            "after": tk.StringVar(value="0.08"),
        }
        self._build_labeled_combo(window_tab, "레이아웃", window_vars["layout"], [label for _, label in WINDOW_LAYOUT_OPTIONS], 0, 0)
        self._build_labeled_combo(window_tab, "동작", window_vars["mode"], ["클릭", "드래그"], 0, 1)
        window_fields = tk.Frame(window_tab, bg="#ffffff")
        window_fields.grid(row=1, column=0, columnspan=3, sticky="ew")
        self._build_numeric_form(
            window_fields,
            [
                ("기준 X", "base_x"),
                ("기준 Y", "base_y"),
                ("Drag X", "delta_x"),
                ("Drag Y", "delta_y"),
                ("지속시간", "duration"),
                ("후 대기", "after"),
            ],
            window_vars,
        )

        delay_vars = {"seconds": tk.StringVar(value="0.50")}
        self._build_numeric_form(
            delay_tab,
            [("대기(초)", "seconds")],
            delay_vars,
            columns=1,
        )

        def add_wait_from_last(now):
            if state["last_time"] is None:
                return
            delay = round(now - state["last_time"], 2)
            if delay > 0:
                state["steps"].append({"type": "sleep", "seconds": delay})

        def redraw_steps():
            listbox.delete(0, tk.END)
            if not state["steps"]:
                listbox.insert(tk.END, "기록된 스텝 없음")
                return

            for index, step in enumerate(state["steps"], start=1):
                listbox.insert(tk.END, self._format_step(index, step))

        def append_click_step():
            now = time.time()
            add_wait_from_last(now)

            x, y = pyautogui.position()
            state["steps"].append({"type": "click", "x": int(x), "y": int(y), "after": 0.05})
            state["last_time"] = now
            status_var.set(f"클릭 기록: ({x}, {y})")
            redraw_steps()

        def set_drag_start():
            x, y = pyautogui.position()
            state["drag_start"] = (int(x), int(y))
            state["last_time"] = time.time()
            status_var.set(f"드래그 시작점 기록: ({x}, {y})")

        def append_drag_step():
            if state["drag_start"] is None:
                status_var.set("먼저 F9로 드래그 시작점을 기록하세요.")
                return

            now = time.time()
            add_wait_from_last(now)

            end_x, end_y = pyautogui.position()
            start_x, start_y = state["drag_start"]
            state["steps"].append(
                {
                    "type": "drag",
                    "start_x": start_x,
                    "start_y": start_y,
                    "delta_x": int(end_x - start_x),
                    "delta_y": int(end_y - start_y),
                    "duration": 0.25,
                    "after": 0.05,
                }
            )
            state["drag_start"] = None
            state["last_time"] = now
            status_var.set(f"드래그 기록: ({start_x}, {start_y}) -> ({int(end_x)}, {int(end_y)})")
            redraw_steps()

        def finish_recording():
            if not state["recording"]:
                return

            state["recording"] = False
            self.root.after(0, self._restore_gui)
            self.root.after(0, redraw_steps)
            self.root.after(0, lambda: status_var.set("녹화가 종료되었습니다. 저장하거나 스텝을 더 추가하세요."))

        def record_worker():
            while state["recording"]:
                if keyboard.is_pressed("esc"):
                    finish_recording()
                    return

                if keyboard.is_pressed("f8"):
                    self.root.after(0, append_click_step)
                    time.sleep(0.35)
                    continue

                if keyboard.is_pressed("f9"):
                    self.root.after(0, set_drag_start)
                    time.sleep(0.35)
                    continue

                if keyboard.is_pressed("f10"):
                    self.root.after(0, append_drag_step)
                    time.sleep(0.35)
                    continue

                time.sleep(0.03)

        def start_recording():
            if state["recording"]:
                return

            state["steps"].clear()
            state["last_time"] = None
            state["drag_start"] = None
            redraw_steps()
            status_var.set("3초 뒤 녹화가 시작됩니다. F8 클릭, F9 시작점, F10 종료점, ESC 종료")

            def begin():
                state["recording"] = True
                self.root.iconify()
                threading.Thread(target=record_worker, daemon=True).start()

            dialog.after(3000, begin)

        def remove_selected_step():
            selection = listbox.curselection()
            if not selection:
                return
            del state["steps"][selection[0]]
            status_var.set("선택한 스텝을 삭제했습니다.")
            redraw_steps()

        def add_manual_drag():
            try:
                step = {
                    "type": "drag",
                    "start_x": int(drag_vars["start_x"].get()),
                    "start_y": int(drag_vars["start_y"].get()),
                    "delta_x": int(drag_vars["delta_x"].get()),
                    "delta_y": int(drag_vars["delta_y"].get()),
                    "duration": float(drag_vars["duration"].get()),
                    "after": float(drag_vars["after"].get()),
                }
            except ValueError:
                messagebox.showwarning("확인", "드래그 입력값을 다시 확인하세요.", parent=dialog)
                return

            state["steps"].append(step)
            status_var.set("수동 드래그 스텝을 추가했습니다.")
            redraw_steps()

        def add_repeat_pattern():
            try:
                step = {
                    "type": "repeat_click_pattern",
                    "start_x": int(pattern_vars["start_x"].get()),
                    "start_y": int(pattern_vars["start_y"].get()),
                    "delta_x": int(pattern_vars["delta_x"].get()),
                    "delta_y": int(pattern_vars["delta_y"].get()),
                    "count": int(pattern_vars["count"].get()),
                    "after": float(pattern_vars["after"].get()),
                }
            except ValueError:
                messagebox.showwarning("확인", "반복 패턴 입력값을 다시 확인하세요.", parent=dialog)
                return

            if step["count"] <= 0:
                messagebox.showwarning("확인", "횟수는 1 이상이어야 합니다.", parent=dialog)
                return

            state["steps"].append(step)
            status_var.set("반복 클릭 패턴을 추가했습니다.")
            redraw_steps()

        def add_window_pattern():
            try:
                layout_label = window_vars["layout"].get().strip()
                layout_key = next(
                    (item_id for item_id, item_label in WINDOW_LAYOUT_OPTIONS if item_label == layout_label),
                    None,
                )
                if layout_key is None:
                    raise ValueError

                base_x = int(window_vars["base_x"].get())
                base_y = int(window_vars["base_y"].get())
                after = float(window_vars["after"].get())
                mode = window_vars["mode"].get().strip()

                if mode == "클릭":
                    step = {
                        "type": "window_grid_click",
                        "layout": layout_key,
                        "base_x": base_x,
                        "base_y": base_y,
                        "after": after,
                    }
                else:
                    step = {
                        "type": "window_grid_drag",
                        "layout": layout_key,
                        "base_x": base_x,
                        "base_y": base_y,
                        "delta_x": int(window_vars["delta_x"].get()),
                        "delta_y": int(window_vars["delta_y"].get()),
                        "duration": float(window_vars["duration"].get()),
                        "after": after,
                    }
            except ValueError:
                messagebox.showwarning("확인", "창 반복 입력값을 다시 확인하세요.", parent=dialog)
                return

            state["steps"].append(step)
            status_var.set("창 반복 스텝을 추가했습니다.")
            redraw_steps()

        def add_manual_delay():
            try:
                seconds = float(delay_vars["seconds"].get())
            except ValueError:
                messagebox.showwarning("확인", "대기 시간을 숫자로 입력하세요.", parent=dialog)
                return

            state["steps"].append({"type": "sleep", "seconds": seconds})
            status_var.set("대기 스텝을 추가했습니다.")
            redraw_steps()

        def save_recording():
            label = name_var.get().strip()
            if not label:
                messagebox.showwarning("확인", "버튼 이름을 입력하세요.", parent=dialog)
                return

            if not state["steps"]:
                messagebox.showwarning("확인", "스텝이 비어 있습니다.", parent=dialog)
                return

            try:
                countdown = int(countdown_var.get().strip())
            except ValueError:
                messagebox.showwarning("확인", "카운트다운은 숫자로 입력하세요.", parent=dialog)
                return

            board_label = board_var.get().strip()
            board_id = next((item_id for item_id, item_label in BOARD_OPTIONS if item_label == board_label), None)
            if board_id is None:
                messagebox.showwarning("확인", "배치 위치를 선택하세요.", parent=dialog)
                return

            provider.save_action(
                label=label,
                steps=state["steps"],
                board=board_id,
                pre_focus=focus_var.get().strip(),
                countdown=countdown,
            )
            self._refresh_actions()
            dialog.destroy()
            messagebox.showinfo("저장 완료", f"'{label}' 버튼을 추가했습니다.", parent=self.root)

        def close_dialog():
            state["recording"] = False
            dialog.destroy()

        ttk.Button(action_row, text="녹화 시작", style="Primary.TButton", command=start_recording).pack(side="left")
        ttk.Button(action_row, text="선택 스텝 삭제", style="Danger.TButton", command=remove_selected_step).pack(side="left", padx=8)
        ttk.Button(action_row, text="저장", style="Board.TButton", command=save_recording).pack(side="right")
        ttk.Button(action_row, text="닫기", style="Board.TButton", command=close_dialog).pack(side="right", padx=(0, 8))

        ttk.Button(manual_drag_tab, text="드래그 스텝 추가", style="Board.TButton", command=add_manual_drag).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10)
        )
        ttk.Button(pattern_tab, text="반복 패턴 추가", style="Board.TButton", command=add_repeat_pattern).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10)
        )
        ttk.Button(window_tab, text="창 반복 추가", style="Board.TButton", command=add_window_pattern).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10)
        )
        ttk.Button(delay_tab, text="대기 스텝 추가", style="Board.TButton", command=add_manual_delay).grid(
            row=1, column=0, sticky="ew", padx=10, pady=(6, 10)
        )

        redraw_steps()
        return True

    def open_macro_manager(self):
        provider = self._get_macro_provider()
        if provider is None:
            messagebox.showerror("오류", "사용자 매크로 저장소를 찾을 수 없습니다.", parent=self.root)
            return False

        dialog = tk.Toplevel(self.root)
        dialog.title("동작 관리")
        dialog.geometry("520x480")
        dialog.configure(bg="#f4f7fb")
        dialog.attributes("-topmost", True)
        dialog.transient(self.root)
        dialog.grab_set()

        card = tk.Frame(dialog, bg="#ffffff", highlightbackground="#d8e0ec", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            card,
            text="Saved Macros",
            bg="#ffffff",
            fg="#142033",
            font=("Malgun Gothic", 15, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 6))

        tk.Label(
            card,
            text="사용자 매크로를 삭제하면 즉시 GUI에서도 사라집니다.",
            bg="#ffffff",
            fg="#607086",
            font=("Malgun Gothic", 10),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        listbox = tk.Listbox(card, font=("Consolas", 10), activestyle="none", borderwidth=0, highlightthickness=0)
        listbox.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        actions = provider.load_actions()

        def redraw():
            listbox.delete(0, tk.END)
            if not actions:
                listbox.insert(tk.END, "저장된 사용자 매크로가 없습니다.")
                return

            for item in actions:
                board_label = BOARD_LABELS.get(item.get("board", "l2m_custom"), item.get("board", "l2m_custom"))
                listbox.insert(tk.END, f"{item['label']}    [{board_label}]")

        def delete_selected():
            selection = listbox.curselection()
            if not selection or not actions:
                return

            item = actions[selection[0]]
            answer = messagebox.askyesno(
                "삭제 확인",
                f"'{item['label']}' 버튼을 삭제할까요?",
                parent=dialog,
            )
            if not answer:
                return

            provider.delete_action(item["id"])
            actions[:] = provider.load_actions()
            self._refresh_actions()
            redraw()

        controls = tk.Frame(card, bg="#ffffff")
        controls.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Button(controls, text="삭제", style="Danger.TButton", command=delete_selected).pack(side="left")
        ttk.Button(controls, text="닫기", style="Board.TButton", command=dialog.destroy).pack(side="right")

        redraw()
        return True

    def _build_labeled_entry(self, parent, label, variable, row, column):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=(0, 10))
        parent.columnconfigure(column, weight=1)

        tk.Label(frame, text=label, bg="#ffffff", fg="#142033", font=("Malgun Gothic", 10, "bold")).pack(anchor="w")
        ttk.Entry(frame, textvariable=variable).pack(fill="x", pady=(4, 0))

    def _build_labeled_combo(self, parent, label, variable, values, row, column):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=(0, 10))
        parent.columnconfigure(column, weight=1)

        tk.Label(frame, text=label, bg="#ffffff", fg="#142033", font=("Malgun Gothic", 10, "bold")).pack(anchor="w")
        ttk.Combobox(frame, textvariable=variable, values=values, state="readonly", style="Panel.TCombobox").pack(fill="x", pady=(4, 0))

    def _build_numeric_form(self, parent, fields, variables, columns=3):
        for col in range(columns):
            parent.columnconfigure(col, weight=1)

        for index, (label, key) in enumerate(fields):
            row, col = divmod(index, columns)
            frame = tk.Frame(parent, bg="#ffffff")
            frame.grid(row=row, column=col, sticky="ew", padx=10, pady=(10, 0))
            tk.Label(frame, text=label, bg="#ffffff", fg="#142033", font=("Malgun Gothic", 10, "bold")).pack(anchor="w")
            ttk.Entry(frame, textvariable=variables[key]).pack(fill="x", pady=(4, 0))

    def _format_step(self, index, step):
        step_type = step["type"]

        if step_type == "click":
            return f"{index:02d}. CLICK x={step['x']} y={step['y']} after={step.get('after', 0.05):.2f}"

        if step_type == "sleep":
            return f"{index:02d}. WAIT  {step['seconds']:.2f}s"

        if step_type == "drag":
            return (
                f"{index:02d}. DRAG  start=({step['start_x']}, {step['start_y']}) "
                f"delta=({step['delta_x']}, {step['delta_y']}) "
                f"dur={step.get('duration', 0.25):.2f}"
            )

        if step_type == "repeat_click_pattern":
            return (
                f"{index:02d}. REPEAT start=({step['start_x']}, {step['start_y']}) "
                f"delta=({step['delta_x']}, {step['delta_y']}) x{step['count']}"
            )

        if step_type == "window_grid_click":
            return (
                f"{index:02d}. GRID-CLICK layout={step.get('layout', 'l2m_9_grid')} "
                f"base=({step['base_x']}, {step['base_y']})"
            )

        if step_type == "window_grid_drag":
            return (
                f"{index:02d}. GRID-DRAG layout={step.get('layout', 'l2m_9_grid')} "
                f"base=({step['base_x']}, {step['base_y']}) "
                f"delta=({step['delta_x']}, {step['delta_y']})"
            )

        return f"{index:02d}. {step_type}"

    def _step_summary(self, step):
        return self._format_step(0, step).split(". ", 1)[-1]

    def open_macro_creator(self):
        return self.open_macro_builder()

    def open_macro_builder(self, action_id=None):
        provider = self._get_macro_provider()
        if provider is None:
            messagebox.showerror("오류", "사용자 매크로 저장소를 찾을 수 없습니다.", parent=self.root)
            return False

        existing = provider.get_action(action_id) if action_id else None
        dialog = tk.Toplevel(self.root)
        dialog.title("Macro Builder")
        dialog.geometry("1180x820")
        dialog.minsize(1100, 760)
        dialog.configure(bg="#eef3f8")
        dialog.transient(self.root)
        dialog.grab_set()

        state = {
            "recording": False,
            "steps": deepcopy(existing["steps"]) if existing else [],
            "last_time": None,
            "drag_start": None,
            "selected_index": None,
        }

        name_var = tk.StringVar(value=existing["label"] if existing else "")
        board_var = tk.StringVar(value=BOARD_LABELS.get(existing.get("board", "l2m_custom"), "L2M Custom") if existing else "L2M Custom")
        focus_var = tk.StringVar(value=existing.get("pre_focus", "Lineage2M") if existing else "Lineage2M")
        countdown_var = tk.StringVar(value=str(existing.get("countdown", 3)) if existing else "3")
        loop_mode_var = tk.StringVar(value="무한 반복" if existing and existing.get("loop_infinite") else "횟수 반복")
        loop_count_var = tk.StringVar(value=str(existing.get("loop_count", 1)) if existing else "1")
        status_var = tk.StringVar(value="좌측 타임라인에서 스텝을 선택해 편집하거나 상단 도구로 새 스텝을 추가하세요.")

        root_card = tk.Frame(dialog, bg="#ffffff", highlightbackground="#d5deea", highlightthickness=1)
        root_card.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(root_card, bg="#0f172a")
        header.pack(fill="x")
        tk.Label(header, text="Macro Builder", bg="#0f172a", fg="#f8fafc", font=("Malgun Gothic", 18, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(header, text="녹화, 타임라인 편집, 스텝 속성 편집을 한 화면에서 처리합니다.", bg="#0f172a", fg="#9fb0c8", font=("Malgun Gothic", 10)).pack(anchor="w", padx=18, pady=(0, 16))

        meta = tk.Frame(root_card, bg="#ffffff")
        meta.pack(fill="x", padx=16, pady=(16, 10))
        self._build_labeled_entry(meta, "버튼 이름", name_var, 0, 0)
        self._build_labeled_combo(meta, "배치 위치", board_var, [label for _, label in BOARD_OPTIONS], 0, 1)
        self._build_labeled_entry(meta, "대상 창 제목", focus_var, 1, 0)
        self._build_labeled_entry(meta, "카운트다운", countdown_var, 1, 1)
        self._build_labeled_combo(meta, "반복 모드", loop_mode_var, ["횟수 반복", "무한 반복"], 2, 0)
        self._build_labeled_entry(meta, "반복 횟수", loop_count_var, 2, 1)

        toolbar = tk.Frame(root_card, bg="#ffffff")
        toolbar.pack(fill="x", padx=16, pady=(0, 10))

        paned = tk.PanedWindow(root_card, orient=tk.HORIZONTAL, sashwidth=6, bg="#ffffff")
        paned.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        left = tk.Frame(paned, bg="#f8fafc", highlightbackground="#d8e0ec", highlightthickness=1)
        right = tk.Frame(paned, bg="#ffffff", highlightbackground="#d8e0ec", highlightthickness=1)
        paned.add(left, minsize=430)
        paned.add(right, minsize=520)

        tk.Label(left, text="Step Timeline", bg="#f8fafc", fg="#142033", font=("Malgun Gothic", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        tree = ttk.Treeview(left, columns=("type", "summary"), show="headings", height=18)
        tree.heading("type", text="Type")
        tree.heading("summary", text="Summary")
        tree.column("type", width=140, anchor="center")
        tree.column("summary", width=360, anchor="w")
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        status_bar = tk.Label(left, textvariable=status_var, bg="#f8fafc", fg="#2563eb", anchor="w", justify="left")
        status_bar.pack(fill="x", padx=12, pady=(0, 12))

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        add_tab = tk.Frame(notebook, bg="#ffffff")
        edit_tab = tk.Frame(notebook, bg="#ffffff")
        notebook.add(add_tab, text="Add Steps")
        notebook.add(edit_tab, text="Step Inspector")

        quick_card = tk.LabelFrame(add_tab, text="Quick Capture", bg="#ffffff", fg="#142033", font=("Malgun Gothic", 10, "bold"))
        quick_card.pack(fill="x", padx=12, pady=(12, 10))
        tk.Label(quick_card, text="F8 클릭, F9 드래그 시작, F10 드래그 종료, ESC 녹화 종료", bg="#ffffff", fg="#516072", anchor="w").pack(fill="x", padx=12, pady=(10, 6))

        form_tabs = ttk.Notebook(add_tab)
        form_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        click_tab = tk.Frame(form_tabs, bg="#ffffff")
        drag_tab = tk.Frame(form_tabs, bg="#ffffff")
        repeat_tab = tk.Frame(form_tabs, bg="#ffffff")
        grid_tab = tk.Frame(form_tabs, bg="#ffffff")
        wait_tab = tk.Frame(form_tabs, bg="#ffffff")
        form_tabs.add(click_tab, text="Click")
        form_tabs.add(drag_tab, text="Drag")
        form_tabs.add(repeat_tab, text="Pattern")
        form_tabs.add(grid_tab, text="9-Window")
        form_tabs.add(wait_tab, text="Wait")

        click_vars = {"x": tk.StringVar(), "y": tk.StringVar(), "after": tk.StringVar(value="0.05")}
        drag_vars = {"start_x": tk.StringVar(), "start_y": tk.StringVar(), "delta_x": tk.StringVar(), "delta_y": tk.StringVar(), "duration": tk.StringVar(value="0.25"), "after": tk.StringVar(value="0.05")}
        repeat_vars = {"start_x": tk.StringVar(), "start_y": tk.StringVar(), "delta_x": tk.StringVar(), "delta_y": tk.StringVar(), "count": tk.StringVar(value="3"), "after": tk.StringVar(value="0.08")}
        grid_vars = {"mode": tk.StringVar(value="클릭"), "base_x": tk.StringVar(), "base_y": tk.StringVar(), "delta_x": tk.StringVar(value="0"), "delta_y": tk.StringVar(value="0"), "duration": tk.StringVar(value="0.25"), "after": tk.StringVar(value="0.08")}
        wait_vars = {"seconds": tk.StringVar(value="0.50")}

        self._build_numeric_form(click_tab, [("X", "x"), ("Y", "y"), ("후 대기", "after")], click_vars)
        self._build_numeric_form(drag_tab, [("시작 X", "start_x"), ("시작 Y", "start_y"), ("Delta X", "delta_x"), ("Delta Y", "delta_y"), ("지속시간", "duration"), ("후 대기", "after")], drag_vars)
        self._build_numeric_form(repeat_tab, [("시작 X", "start_x"), ("시작 Y", "start_y"), ("X 증가", "delta_x"), ("Y 증가", "delta_y"), ("횟수", "count"), ("후 대기", "after")], repeat_vars)
        self._build_labeled_combo(grid_tab, "동작", grid_vars["mode"], ["클릭", "드래그"], 0, 0)
        grid_inner = tk.Frame(grid_tab, bg="#ffffff")
        grid_inner.grid(row=1, column=0, columnspan=3, sticky="ew")
        self._build_numeric_form(grid_inner, [("기준 X", "base_x"), ("기준 Y", "base_y"), ("Drag X", "delta_x"), ("Drag Y", "delta_y"), ("지속시간", "duration"), ("후 대기", "after")], grid_vars)
        self._build_numeric_form(wait_tab, [("대기(초)", "seconds")], wait_vars, columns=1)

        inspector_frame = tk.Frame(edit_tab, bg="#ffffff")
        inspector_frame.pack(fill="x", padx=12, pady=(12, 8))
        inspector_vars = {key: tk.StringVar() for key in ("type", "x", "y", "start_x", "start_y", "delta_x", "delta_y", "count", "seconds", "duration", "after")}
        self._build_labeled_entry(inspector_frame, "Type", inspector_vars["type"], 0, 0)
        self._build_labeled_entry(inspector_frame, "X", inspector_vars["x"], 0, 1)
        self._build_labeled_entry(inspector_frame, "Y", inspector_vars["y"], 0, 2)
        self._build_labeled_entry(inspector_frame, "Start X", inspector_vars["start_x"], 1, 0)
        self._build_labeled_entry(inspector_frame, "Start Y", inspector_vars["start_y"], 1, 1)
        self._build_labeled_entry(inspector_frame, "Delta X", inspector_vars["delta_x"], 1, 2)
        self._build_labeled_entry(inspector_frame, "Delta Y", inspector_vars["delta_y"], 2, 0)
        self._build_labeled_entry(inspector_frame, "Count", inspector_vars["count"], 2, 1)
        self._build_labeled_entry(inspector_frame, "Seconds", inspector_vars["seconds"], 2, 2)
        self._build_labeled_entry(inspector_frame, "Duration", inspector_vars["duration"], 3, 0)
        self._build_labeled_entry(inspector_frame, "After", inspector_vars["after"], 3, 1)

        def selected_step():
            idx = state["selected_index"]
            if idx is None or idx < 0 or idx >= len(state["steps"]):
                return None
            return state["steps"][idx]

        def load_selected_into_editor(event=None):
            selection = tree.selection()
            if selection:
                state["selected_index"] = int(selection[0])

            step = selected_step()
            for var in inspector_vars.values():
                var.set("")
            if not step:
                return

            inspector_vars["type"].set(step.get("type", ""))
            if step.get("type") == "click":
                inspector_vars["x"].set(str(step.get("x", "")))
                inspector_vars["y"].set(str(step.get("y", "")))
            if step.get("type") in ("drag", "repeat_click_pattern"):
                for key in ("start_x", "start_y", "delta_x", "delta_y"):
                    inspector_vars[key].set(str(step.get(key, "")))
            if step.get("type") == "sleep":
                inspector_vars["seconds"].set(str(step.get("seconds", "")))
            if step.get("type") == "repeat_click_pattern":
                inspector_vars["count"].set(str(step.get("count", "")))
            if step.get("type") in ("drag", "window_grid_drag"):
                inspector_vars["duration"].set(str(step.get("duration", "")))
            if step.get("type") in ("click", "drag", "repeat_click_pattern", "window_grid_click", "window_grid_drag"):
                inspector_vars["after"].set(str(step.get("after", "")))
            if step.get("type") in ("window_grid_click", "window_grid_drag"):
                inspector_vars["x"].set(str(step.get("base_x", "")))
                inspector_vars["y"].set(str(step.get("base_y", "")))
                inspector_vars["delta_x"].set(str(step.get("delta_x", "")))
                inspector_vars["delta_y"].set(str(step.get("delta_y", "")))

        def refresh_tree(select_index=None):
            tree.delete(*tree.get_children())
            for index, step in enumerate(state["steps"]):
                tree.insert("", "end", iid=str(index), values=(step["type"], self._step_summary(step)))
            if select_index is not None and 0 <= select_index < len(state["steps"]):
                tree.selection_set(str(select_index))
                tree.focus(str(select_index))
                tree.see(str(select_index))
                state["selected_index"] = select_index
            else:
                state["selected_index"] = None
            load_selected_into_editor()

        def append_step(step):
            state["steps"].append(step)
            refresh_tree(len(state["steps"]) - 1)

        def add_wait_from_last(now):
            if state["last_time"] is None:
                return
            delay = round(now - state["last_time"], 2)
            if delay > 0:
                state["steps"].append({"type": "sleep", "seconds": delay})

        def record_click():
            now = time.time()
            add_wait_from_last(now)
            x, y = pyautogui.position()
            append_step({"type": "click", "x": int(x), "y": int(y), "after": 0.05})
            state["last_time"] = now
            status_var.set(f"클릭 기록: ({x}, {y})")

        def record_drag_start():
            x, y = pyautogui.position()
            state["drag_start"] = (int(x), int(y))
            state["last_time"] = time.time()
            status_var.set(f"드래그 시작점: ({x}, {y})")

        def record_drag_end():
            if state["drag_start"] is None:
                status_var.set("먼저 F9로 드래그 시작점을 기록하세요.")
                return
            now = time.time()
            add_wait_from_last(now)
            end_x, end_y = pyautogui.position()
            start_x, start_y = state["drag_start"]
            append_step({"type": "drag", "start_x": start_x, "start_y": start_y, "delta_x": int(end_x - start_x), "delta_y": int(end_y - start_y), "duration": 0.25, "after": 0.05})
            state["drag_start"] = None
            state["last_time"] = now
            status_var.set(f"드래그 기록: ({start_x}, {start_y}) -> ({int(end_x)}, {int(end_y)})")

        def stop_recording():
            state["recording"] = False
            self.root.after(0, self._restore_gui)
            self.root.after(0, lambda: status_var.set("녹화가 종료되었습니다."))

        def record_worker():
            while state["recording"]:
                if keyboard.is_pressed("esc"):
                    stop_recording()
                    return
                if keyboard.is_pressed("f8"):
                    self.root.after(0, record_click)
                    time.sleep(0.35)
                    continue
                if keyboard.is_pressed("f9"):
                    self.root.after(0, record_drag_start)
                    time.sleep(0.35)
                    continue
                if keyboard.is_pressed("f10"):
                    self.root.after(0, record_drag_end)
                    time.sleep(0.35)
                    continue
                time.sleep(0.03)

        def start_recording():
            if state["recording"]:
                return
            state["last_time"] = None
            state["drag_start"] = None
            status_var.set("3초 뒤 녹화를 시작합니다. F8/F9/F10/ESC를 사용하세요.")

            def begin():
                state["recording"] = True
                self.root.iconify()
                threading.Thread(target=record_worker, daemon=True).start()

            dialog.after(3000, begin)

        def build_step_from_editor():
            step_type = inspector_vars["type"].get().strip()
            if step_type == "click":
                return {"type": "click", "x": int(inspector_vars["x"].get()), "y": int(inspector_vars["y"].get()), "after": float(inspector_vars["after"].get() or 0.05)}
            if step_type == "sleep":
                return {"type": "sleep", "seconds": float(inspector_vars["seconds"].get())}
            if step_type == "drag":
                return {"type": "drag", "start_x": int(inspector_vars["start_x"].get()), "start_y": int(inspector_vars["start_y"].get()), "delta_x": int(inspector_vars["delta_x"].get()), "delta_y": int(inspector_vars["delta_y"].get()), "duration": float(inspector_vars["duration"].get() or 0.25), "after": float(inspector_vars["after"].get() or 0.05)}
            if step_type == "repeat_click_pattern":
                return {"type": "repeat_click_pattern", "start_x": int(inspector_vars["start_x"].get()), "start_y": int(inspector_vars["start_y"].get()), "delta_x": int(inspector_vars["delta_x"].get()), "delta_y": int(inspector_vars["delta_y"].get()), "count": int(inspector_vars["count"].get()), "after": float(inspector_vars["after"].get() or 0.08)}
            if step_type == "window_grid_click":
                return {"type": "window_grid_click", "layout": "l2m_9_grid", "base_x": int(inspector_vars["x"].get()), "base_y": int(inspector_vars["y"].get()), "after": float(inspector_vars["after"].get() or 0.08)}
            if step_type == "window_grid_drag":
                return {"type": "window_grid_drag", "layout": "l2m_9_grid", "base_x": int(inspector_vars["x"].get()), "base_y": int(inspector_vars["y"].get()), "delta_x": int(inspector_vars["delta_x"].get()), "delta_y": int(inspector_vars["delta_y"].get()), "duration": float(inspector_vars["duration"].get() or 0.25), "after": float(inspector_vars["after"].get() or 0.08)}
            raise ValueError("지원하지 않는 step type")

        def apply_selected_changes():
            idx = state["selected_index"]
            if idx is None:
                return
            try:
                state["steps"][idx] = build_step_from_editor()
            except Exception:
                messagebox.showwarning("확인", "선택 스텝 입력값을 다시 확인하세요.", parent=dialog)
                return
            refresh_tree(idx)
            status_var.set("선택한 스텝을 수정했습니다.")

        def add_click_manual():
            try:
                append_step({"type": "click", "x": int(click_vars["x"].get()), "y": int(click_vars["y"].get()), "after": float(click_vars["after"].get())})
            except ValueError:
                messagebox.showwarning("확인", "클릭 입력값을 다시 확인하세요.", parent=dialog)
                return
            status_var.set("클릭 스텝을 추가했습니다.")

        def add_drag_manual():
            try:
                append_step({"type": "drag", "start_x": int(drag_vars["start_x"].get()), "start_y": int(drag_vars["start_y"].get()), "delta_x": int(drag_vars["delta_x"].get()), "delta_y": int(drag_vars["delta_y"].get()), "duration": float(drag_vars["duration"].get()), "after": float(drag_vars["after"].get())})
            except ValueError:
                messagebox.showwarning("확인", "드래그 입력값을 다시 확인하세요.", parent=dialog)
                return
            status_var.set("드래그 스텝을 추가했습니다.")

        def add_repeat_manual():
            try:
                append_step({"type": "repeat_click_pattern", "start_x": int(repeat_vars["start_x"].get()), "start_y": int(repeat_vars["start_y"].get()), "delta_x": int(repeat_vars["delta_x"].get()), "delta_y": int(repeat_vars["delta_y"].get()), "count": int(repeat_vars["count"].get()), "after": float(repeat_vars["after"].get())})
            except ValueError:
                messagebox.showwarning("확인", "반복 패턴 입력값을 다시 확인하세요.", parent=dialog)
                return
            status_var.set("반복 패턴 스텝을 추가했습니다.")

        def add_grid_manual():
            try:
                if grid_vars["mode"].get() == "클릭":
                    append_step({"type": "window_grid_click", "layout": "l2m_9_grid", "base_x": int(grid_vars["base_x"].get()), "base_y": int(grid_vars["base_y"].get()), "after": float(grid_vars["after"].get())})
                else:
                    append_step({"type": "window_grid_drag", "layout": "l2m_9_grid", "base_x": int(grid_vars["base_x"].get()), "base_y": int(grid_vars["base_y"].get()), "delta_x": int(grid_vars["delta_x"].get()), "delta_y": int(grid_vars["delta_y"].get()), "duration": float(grid_vars["duration"].get()), "after": float(grid_vars["after"].get())})
            except ValueError:
                messagebox.showwarning("확인", "9창 반복 입력값을 다시 확인하세요.", parent=dialog)
                return
            status_var.set("9창 반복 스텝을 추가했습니다.")

        def add_wait_manual():
            try:
                append_step({"type": "sleep", "seconds": float(wait_vars["seconds"].get())})
            except ValueError:
                messagebox.showwarning("확인", "대기 시간을 다시 확인하세요.", parent=dialog)
                return
            status_var.set("대기 스텝을 추가했습니다.")

        def duplicate_selected():
            step = selected_step()
            if not step:
                return
            idx = state["selected_index"] + 1
            state["steps"].insert(idx, deepcopy(step))
            refresh_tree(idx)

        def delete_selected():
            idx = state["selected_index"]
            if idx is None:
                return
            del state["steps"][idx]
            refresh_tree(min(idx, len(state["steps"]) - 1))

        def move_selected(delta):
            idx = state["selected_index"]
            if idx is None:
                return
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(state["steps"]):
                return
            state["steps"][idx], state["steps"][new_idx] = state["steps"][new_idx], state["steps"][idx]
            refresh_tree(new_idx)

        def save_macro():
            label = name_var.get().strip()
            if not label:
                messagebox.showwarning("확인", "버튼 이름을 입력하세요.", parent=dialog)
                return
            if not state["steps"]:
                messagebox.showwarning("확인", "스텝이 비어 있습니다.", parent=dialog)
                return
            try:
                countdown = int(countdown_var.get().strip())
            except ValueError:
                messagebox.showwarning("확인", "카운트다운은 숫자로 입력하세요.", parent=dialog)
                return
            try:
                loop_count = int(loop_count_var.get().strip())
            except ValueError:
                messagebox.showwarning("확인", "반복 횟수는 숫자로 입력하세요.", parent=dialog)
                return
            if loop_count <= 0:
                messagebox.showwarning("확인", "반복 횟수는 1 이상이어야 합니다.", parent=dialog)
                return
            loop_infinite = loop_mode_var.get() == "무한 반복"

            board_id = next((item_id for item_id, item_label in BOARD_OPTIONS if item_label == board_var.get().strip()), "l2m_custom")

            if existing:
                provider.update_action(
                    existing["id"],
                    label=label,
                    steps=state["steps"],
                    board=board_id,
                    pre_focus=focus_var.get().strip(),
                    countdown=countdown,
                    loop_count=loop_count,
                    loop_infinite=loop_infinite,
                )
            else:
                provider.save_action(
                    label=label,
                    steps=state["steps"],
                    board=board_id,
                    pre_focus=focus_var.get().strip(),
                    countdown=countdown,
                    loop_count=loop_count,
                    loop_infinite=loop_infinite,
                )

            self._refresh_actions()
            dialog.destroy()
            messagebox.showinfo("저장 완료", f"'{label}' 매크로를 저장했습니다.", parent=self.root)

        def close_dialog():
            state["recording"] = False
            dialog.destroy()

        ttk.Button(toolbar, text="녹화 시작", style="Primary.TButton", command=start_recording).pack(side="left")
        ttk.Button(toolbar, text="복제", style="Board.TButton", command=duplicate_selected).pack(side="left", padx=6)
        ttk.Button(toolbar, text="위로", style="Board.TButton", command=lambda: move_selected(-1)).pack(side="left", padx=6)
        ttk.Button(toolbar, text="아래로", style="Board.TButton", command=lambda: move_selected(1)).pack(side="left", padx=6)
        ttk.Button(toolbar, text="삭제", style="Danger.TButton", command=delete_selected).pack(side="left", padx=6)
        ttk.Button(toolbar, text="선택 스텝 적용", style="Board.TButton", command=apply_selected_changes).pack(side="right")
        ttk.Button(toolbar, text="저장", style="Board.TButton", command=save_macro).pack(side="right", padx=6)
        ttk.Button(toolbar, text="닫기", style="Board.TButton", command=close_dialog).pack(side="right", padx=6)

        ttk.Button(quick_card, text="현재 마우스 클릭 추가", style="Board.TButton", command=record_click).pack(anchor="w", padx=12, pady=(0, 10))
        ttk.Button(click_tab, text="클릭 스텝 추가", style="Board.TButton", command=add_click_manual).grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10))
        ttk.Button(drag_tab, text="드래그 스텝 추가", style="Board.TButton", command=add_drag_manual).grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10))
        ttk.Button(repeat_tab, text="반복 패턴 추가", style="Board.TButton", command=add_repeat_manual).grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10))
        ttk.Button(grid_tab, text="9창 반복 추가", style="Board.TButton", command=add_grid_manual).grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 10))
        ttk.Button(wait_tab, text="대기 스텝 추가", style="Board.TButton", command=add_wait_manual).grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 10))

        tree.bind("<<TreeviewSelect>>", load_selected_into_editor)
        refresh_tree(0 if state["steps"] else None)
        return True

    def open_macro_manager(self):
        provider = self._get_macro_provider()
        if provider is None:
            messagebox.showerror("오류", "사용자 매크로 저장소를 찾을 수 없습니다.", parent=self.root)
            return False

        dialog = tk.Toplevel(self.root)
        dialog.title("동작 관리")
        dialog.geometry("620x520")
        dialog.configure(bg="#eef3f8")
        dialog.transient(self.root)
        dialog.grab_set()

        card = tk.Frame(dialog, bg="#ffffff", highlightbackground="#d8e0ec", highlightthickness=1)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(card, text="Saved Macros", bg="#ffffff", fg="#142033", font=("Malgun Gothic", 15, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(card, text="편집 또는 삭제할 매크로를 선택하세요.", bg="#ffffff", fg="#607086", font=("Malgun Gothic", 10)).pack(anchor="w", padx=16, pady=(0, 10))

        tree = ttk.Treeview(card, columns=("label", "board"), show="headings", height=14)
        tree.heading("label", text="Macro")
        tree.heading("board", text="Board")
        tree.column("label", width=340, anchor="w")
        tree.column("board", width=180, anchor="center")
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        actions = provider.load_actions()
        for index, item in enumerate(actions):
            tree.insert("", "end", iid=str(index), values=(item["label"], BOARD_LABELS.get(item.get("board", "l2m_custom"), item.get("board", "l2m_custom"))))

        def selected_action():
            selection = tree.selection()
            if not selection:
                return None
            idx = int(selection[0])
            if idx < 0 or idx >= len(actions):
                return None
            return actions[idx]

        def edit_selected():
            item = selected_action()
            if not item:
                return
            dialog.destroy()
            self.open_macro_builder(item["id"])

        def delete_selected():
            item = selected_action()
            if not item:
                return
            if not messagebox.askyesno("삭제 확인", f"'{item['label']}' 매크로를 삭제할까요?", parent=dialog):
                return
            provider.delete_action(item["id"])
            self._refresh_actions()
            dialog.destroy()
            self.open_macro_manager()

        controls = tk.Frame(card, bg="#ffffff")
        controls.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(controls, text="편집", style="Primary.TButton", command=edit_selected).pack(side="left")
        ttk.Button(controls, text="삭제", style="Danger.TButton", command=delete_selected).pack(side="left", padx=8)
        ttk.Button(controls, text="닫기", style="Board.TButton", command=dialog.destroy).pack(side="right")

        return True

    def _set_today_schedule(self):
        schedule.clear()
        self.schedule_items.clear()

        for spec in self.schedule_specs:
            if not spec.enabled:
                continue

            time_str = spec.time_picker()
            schedule.every().day.at(time_str).do(spec.runner)
            self.schedule_items[spec.id] = {
                "label": spec.label,
                "time": time_str,
            }

        self._update_schedule_label()
        self._update_health_label()

    def _scheduler_tick(self):
        try:
            schedule.run_pending()
        except Exception:
            log_exc("SCHEDULER")

        if datetime.now().day != self.last_day:
            self.last_day = datetime.now().day
            self._set_today_schedule()

        self._update_health_label()

        self.root.after(1000, self._scheduler_tick)

    def _on_close(self):
        try:
            schedule.clear()
        except Exception:
            pass

        self._stop_all_running_actions()

        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = ControlCenterApp()
    app.run()


if __name__ == "__main__":
    main()
