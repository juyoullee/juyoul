import json
import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog

import keyboard
import pyautogui
import win32con
import win32gui
from PIL import Image, ImageTk, ImageGrab

from Core.action_base import ActionsBase
from Core.action_specs import ActionSpec

_BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_IMAGES_DIR = os.path.join(_BASE_DIR, "nightcrow_images")
_IMAGES_JSON = os.path.join(_BASE_DIR, "nightcrow_images.json")

_CLICK_OPTIONS = ["좌클릭", "우클릭", "더블클릭"]
_CLICK_MAP = {"좌클릭": "left", "우클릭": "right", "더블클릭": "double"}
_CLICK_LABEL = {v: k for k, v in _CLICK_MAP.items()}


class NightCrowImageSearch(ActionsBase):
    def __init__(self):
        super().__init__()
        self._running = False
        self._panel = None
        os.makedirs(_IMAGES_DIR, exist_ok=True)
        self._items = self._load_items()

    def _load_items(self):
        try:
            with open(_IMAGES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and isinstance(data[0], str):
                return [{"path": p, "click_type": "left"} for p in data]
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_items(self):
        with open(_IMAGES_JSON, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)

    def get_action_specs(self):
        return [
            ActionSpec(
                id="nightcrow.panel",
                label="이미지 서치",
                runner=self._open_panel,
                board="nightcrow",
                countdown=0,
                background=False,
                minimize_gui=False,
            ),
            ActionSpec(
                id="nightcrow.maximize1",
                label="1번창 최대화",
                runner=lambda: self._maximize_game_window("NIGHT CROWS(1)"),
                board="nightcrow",
                countdown=0,
                background=False,
                minimize_gui=False,
            ),
            ActionSpec(
                id="nightcrow.maximize2",
                label="2번창 최대화",
                runner=lambda: self._maximize_game_window("NIGHT CROWS(2)"),
                board="nightcrow",
                countdown=0,
                background=False,
                minimize_gui=False,
            ),
        ]

    def _maximize_game_window(self, window_title):
        matched = []

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if window_title in title:
                    matched.append(hwnd)

        win32gui.EnumWindows(_enum, None)
        if matched:
            win32gui.ShowWindow(matched[0], win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(matched[0])

    def _open_panel(self):
        if self._panel and self._panel.is_open():
            self._panel.lift()
            return
        self._panel = NightCrowPanel(
            items=self._items,
            images_dir=_IMAGES_DIR,
            on_items_changed=self._on_items_changed,
            on_start=self._start_loop,
            on_stop=self._stop_loop,
            is_running=lambda: self._running,
        )
        self._panel.open()

    def _on_items_changed(self, items):
        self._items = items
        self._save_items()

    def _start_loop(self):
        if self._running:
            return
        self._running = True
        self.RUNNING = True
        threading.Thread(target=self._search_loop, daemon=True).start()

    def _stop_loop(self):
        self._running = False
        self.RUNNING = False
        self._restore_panel()

    def _restore_panel(self):
        if self._panel and self._panel.is_open():
            self._panel.schedule_restore()

    def _search_loop(self):
        while self._running and self.RUNNING:
            if keyboard.is_pressed("esc"):
                self._running = False
                self.RUNNING = False
                break

            for item in list(self._items):
                if not self._running:
                    break
                path = item.get("path", "")
                click_type = item.get("click_type", "left")
                if not os.path.exists(path):
                    continue
                try:
                    try:
                        loc = pyautogui.locateOnScreen(path, confidence=0.8)
                    except TypeError:
                        loc = pyautogui.locateOnScreen(path)

                    if loc:
                        margin_x = max(2, int(loc.width * 0.15))
                        margin_y = max(2, int(loc.height * 0.15))
                        tx = random.randint(loc.left + margin_x, loc.left + loc.width - margin_x)
                        ty = random.randint(loc.top + margin_y, loc.top + loc.height - margin_y)

                        pyautogui.moveTo(tx, ty, duration=random.uniform(0.10, 0.30))
                        time.sleep(random.uniform(0.04, 0.12))

                        if click_type == "right":
                            pyautogui.click(button="right")
                        elif click_type == "double":
                            pyautogui.doubleClick()
                        else:
                            pyautogui.click()

                        time.sleep(random.uniform(0.35, 0.75))

                except pyautogui.ImageNotFoundException:
                    pass
                except Exception:
                    pass

            time.sleep(random.uniform(0.7, 1.6))

        self._running = False
        self._restore_panel()


class _ScreenCaptureOverlay:
    def __init__(self):
        self._region = None
        self._start_x = 0
        self._start_y = 0
        self._rect_id = None

        self._win = tk.Toplevel()
        self._win.attributes("-fullscreen", True)
        self._win.attributes("-alpha", 0.35)
        self._win.attributes("-topmost", True)
        self._win.overrideredirect(True)
        self._win.configure(bg="black")

        self._canvas = tk.Canvas(
            self._win,
            bg="black",
            cursor="crosshair",
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)

        tk.Label(
            self._win,
            text="드래그하여 영역 선택   |   ESC: 취소",
            bg="black",
            fg="#00ff00",
            font=("Malgun Gothic", 12, "bold"),
        ).place(relx=0.5, rely=0.04, anchor="center")

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._win.bind("<Escape>", lambda _: self._win.destroy())
        self._win.after(50, self._canvas.focus_force)

    def capture(self):
        self._win.wait_window()
        if self._region is None:
            return None
        time.sleep(0.08)
        return ImageGrab.grab(bbox=self._region)

    def _on_press(self, event):
        self._start_x = event.x
        self._start_y = event.y
        if self._rect_id:
            self._canvas.delete(self._rect_id)

    def _on_drag(self, event):
        if self._rect_id:
            self._canvas.delete(self._rect_id)
        self._rect_id = self._canvas.create_rectangle(
            self._start_x, self._start_y, event.x, event.y,
            outline="#00ff00", width=2,
        )

    def _on_release(self, event):
        x1 = min(self._start_x, event.x)
        y1 = min(self._start_y, event.y)
        x2 = max(self._start_x, event.x)
        y2 = max(self._start_y, event.y)
        if x2 - x1 >= 5 and y2 - y1 >= 5:
            self._region = (x1, y1, x2, y2)
        self._win.destroy()


class NightCrowPanel:
    def __init__(self, items, images_dir, on_items_changed, on_start, on_stop, is_running):
        self._items = list(items)
        self._images_dir = images_dir
        self._on_items_changed = on_items_changed
        self._on_start = on_start
        self._on_stop = on_stop
        self._is_running = is_running
        self._win = None
        self._status_label = None
        self._start_btn = None
        self._stop_btn = None
        self._list_frame = None
        self._tick_id = None

    def open(self):
        self._win = tk.Toplevel()
        self._win.title("Night Crow - 이미지 서치")
        self._win.geometry("520x600")
        self._win.configure(bg="#0b1220")
        self._win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._win.lift()
        self._win.focus_force()
        self._tick()

    def restore(self):
        if self.is_open():
            self._win.deiconify()
            self._win.lift()
            self._win.focus_force()

    def schedule_restore(self):
        if self.is_open():
            self._win.after(0, self.restore)

    def is_open(self):
        return self._win is not None and self._win.winfo_exists()

    def lift(self):
        if self.is_open():
            self._win.lift()
            self._win.focus_force()

    def _on_start_clicked(self):
        self._on_start()
        if self.is_open():
            self._win.iconify()

    def _on_close(self):
        if self._tick_id:
            self._win.after_cancel(self._tick_id)
        self._win.destroy()
        self._win = None

    def _maximize_game_window(self, window_title):
        matched = []

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if window_title in title:
                    matched.append(hwnd)

        win32gui.EnumWindows(_enum, None)
        if matched:
            win32gui.ShowWindow(matched[0], win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(matched[0])

    def _build_ui(self):
        status_bar = tk.Frame(self._win, bg="#131f2e")
        status_bar.pack(fill="x", padx=12, pady=(12, 0))

        self._status_label = tk.Label(
            status_bar,
            text="● 대기 중",
            bg="#131f2e",
            fg="#4ade80",
            font=("Malgun Gothic", 10, "bold"),
        )
        self._status_label.pack(side="left", padx=10, pady=7)

        ctrl_frame = tk.Frame(self._win, bg="#0b1220")
        ctrl_frame.pack(fill="x", padx=12, pady=(8, 4))

        self._start_btn = ttk.Button(
            ctrl_frame,
            text="시작",
            style="Primary.TButton",
            command=self._on_start_clicked,
        )
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = ttk.Button(
            ctrl_frame,
            text="종료",
            style="Danger.TButton",
            command=self._on_stop,
        )
        self._stop_btn.pack(side="left")
        self._stop_btn.state(["disabled"])

        toolbar = tk.Frame(self._win, bg="#0b1220")
        toolbar.pack(fill="x", padx=12, pady=(6, 4))

        ttk.Button(
            toolbar,
            text="화면 캡처",
            style="Board.TButton",
            command=self._capture_screen,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar,
            text="파일 추가",
            style="Board.TButton",
            command=self._add_files,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar,
            text="1번창 최대화",
            style="Board.TButton",
            command=lambda: self._maximize_game_window("NIGHT CROWS(1)"),
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            toolbar,
            text="2번창 최대화",
            style="Board.TButton",
            command=lambda: self._maximize_game_window("NIGHT CROWS(2)"),
        ).pack(side="left")

        sep = tk.Frame(self._win, bg="#1e2d40", height=1)
        sep.pack(fill="x", padx=12, pady=(4, 0))

        tk.Label(
            self._win,
            text="이미지 목록",
            bg="#0b1220",
            fg="#8da2c0",
            font=("Malgun Gothic", 9),
        ).pack(anchor="w", padx=14, pady=(6, 2))

        list_container = tk.Frame(self._win, bg="#0b1220")
        list_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._canvas = tk.Canvas(list_container, bg="#0b1220", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._list_frame = tk.Frame(self._canvas, bg="#0b1220")
        win_id = self._canvas.create_window((0, 0), window=self._list_frame, anchor="nw")

        self._list_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfigure(win_id, width=e.width),
        )
        self._canvas.bind(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        self._render_list()

    def _render_list(self):
        for child in self._list_frame.winfo_children():
            child.destroy()

        if not self._items:
            tk.Label(
                self._list_frame,
                text="등록된 이미지가 없습니다.\n화면 캡처 또는 파일 추가로 이미지를 등록하세요.",
                bg="#0b1220",
                fg="#7f8a9a",
                font=("Malgun Gothic", 10),
                justify="center",
            ).pack(pady=24)
            return

        for i, item in enumerate(self._items):
            path = item.get("path", "")
            click_type = item.get("click_type", "left")

            row = tk.Frame(self._list_frame, bg="#131f2e", pady=6)
            row.pack(fill="x", pady=2)

            thumb = tk.Label(row, bg="#131f2e")
            thumb.pack(side="left", padx=(8, 8))
            self._load_thumbnail(thumb, path)

            info_frame = tk.Frame(row, bg="#131f2e")
            info_frame.pack(side="left", fill="x", expand=True)

            tk.Label(
                info_frame,
                text=os.path.basename(path),
                bg="#131f2e",
                fg="#c8d8e8",
                font=("Malgun Gothic", 9, "bold"),
                anchor="w",
            ).pack(fill="x")

            exists = os.path.exists(path)
            tk.Label(
                info_frame,
                text="✓ 파일 있음" if exists else "✗ 파일 없음",
                bg="#131f2e",
                fg="#4ade80" if exists else "#f87171",
                font=("Malgun Gothic", 8),
                anchor="w",
            ).pack(fill="x")

            action_frame = tk.Frame(row, bg="#131f2e")
            action_frame.pack(side="right", padx=8)

            click_var = tk.StringVar(value=_CLICK_LABEL.get(click_type, "좌클릭"))
            combo = ttk.Combobox(
                action_frame,
                textvariable=click_var,
                values=_CLICK_OPTIONS,
                state="readonly",
                width=7,
            )
            combo.pack(side="top", pady=(0, 4))
            combo.bind(
                "<<ComboboxSelected>>",
                lambda e, idx=i, var=click_var: self._on_click_type_changed(idx, var.get()),
            )

            ttk.Button(
                action_frame,
                text="삭제",
                style="Board.TButton",
                command=lambda ix=i: self._remove(ix),
            ).pack(side="top")

    def _on_click_type_changed(self, index, label):
        if 0 <= index < len(self._items):
            self._items[index]["click_type"] = _CLICK_MAP.get(label, "left")
            self._on_items_changed(self._items)

    def _load_thumbnail(self, label, path):
        try:
            img = Image.open(path)
            img.thumbnail((52, 40))
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo, width=52, height=40)
            label.image = photo
        except Exception:
            label.configure(text="?", fg="#7f8a9a", width=5, height=2)

    def _capture_screen(self):
        self._win.withdraw()
        overlay = _ScreenCaptureOverlay()
        img = overlay.capture()
        self._win.deiconify()
        self._win.lift()

        if img is None:
            return

        existing = [f for f in os.listdir(self._images_dir) if f.lower().endswith(".png")]
        save_path = os.path.join(self._images_dir, f"capture_{len(existing) + 1:03d}.png")
        img.save(save_path)
        self._items.append({"path": save_path, "click_type": "left"})
        self._on_items_changed(self._items)
        self._render_list()

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="이미지 파일 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp"), ("모든 파일", "*.*")],
            parent=self._win,
        )
        existing_paths = {it["path"] for it in self._items}
        changed = False
        for path in files:
            if path and path not in existing_paths:
                self._items.append({"path": path, "click_type": "left"})
                changed = True
        if changed:
            self._on_items_changed(self._items)
            self._render_list()

    def _remove(self, index):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self._on_items_changed(self._items)
            self._render_list()

    def _tick(self):
        if not self.is_open():
            return
        running = self._is_running()
        if self._status_label:
            if running:
                self._status_label.config(text="● 실행 중", fg="#60a5fa")
            else:
                self._status_label.config(text="● 대기 중", fg="#4ade80")
        if self._start_btn:
            self._start_btn.state(["disabled"] if running else ["!disabled"])
        if self._stop_btn:
            self._stop_btn.state(["!disabled"] if running else ["disabled"])
        self._tick_id = self._win.after(500, self._tick)
