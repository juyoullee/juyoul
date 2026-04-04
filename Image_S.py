import cv2
import pyautogui
import time
import threading
import numpy as np
import tkinter as tk
import random
import keyboard

# ================================
# 상태 변수
# ================================
running = True
paused = False
CLICK_INTERVAL = 1.0
DELAY_MIN = 0.5
DELAY_MAX = 1.0

# ================================
# 1) 이미지별 다른 동작 정의
# ================================
def action_skip(x, y):
    x,y = pyautogui.position()
    pyautogui.click(x,y)




def action_agree(x, y):
    pyautogui.click(x, y)
    # time.sleep(0.5)
    # pyautogui.click(x -250, y+50)

def action_pass(x, y):
    pyautogui.click(x, y)
    time.sleep(0.3)
    pyautogui.click(x +250, y -120)



# ================================
# 2) 이미지 설정
# ================================
targets = [
    # {"name": "Clear","path": "Clear.png",       "threshold": 0.85, "action": action_skip},
    {"name": "skip","path": "skip.png",     "threshold": 0.85, "action": action_agree},
    {"name": "skip2","path": "comp.png",     "threshold": 0.85, "action" : action_pass},

]

for t in targets:
    img = cv2.imread(t["path"], cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"이미지 로드 실패: {t['path']}")
    t["image"] = img
    t["last_click"] = 0.0

# ================================
# 3) 메인 반복
# ================================
def click_loop():
    global running, paused
    while running:
        if paused:
            time.sleep(1)
            continue

        screenshot = pyautogui.screenshot()
        gray_screen = cv2.cvtColor(
            cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR),
            cv2.COLOR_BGR2GRAY
        )

        now = time.time()

        for t in targets:
            result = cv2.matchTemplate(gray_screen, t["image"], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= t["threshold"] and (now - t["last_click"]) >= CLICK_INTERVAL:
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                cx = max_loc[0] + t["image"].shape[1] // 2
                cy = max_loc[1] + t["image"].shape[0] // 2
                rx = cx + random.randint(-2, 2)
                ry = cy + random.randint(-2, 2)

                t["action"](rx, ry)
                t["last_click"] = time.time()

        time.sleep(1)

# ================================
# 4) 제어 함수
# ================================
def toggle_pause():
    global paused
    paused = not paused
    status_label.config(text="상태: 일시정지" if paused else "상태: 실행 중")

def stop_program():
    global running
    running = False
    root.destroy()

# ================================
# 5) 단축키
# ================================
keyboard.add_hotkey("F8", toggle_pause)
keyboard.add_hotkey("ESC", stop_program)

# ================================
# 6) GUI
# ================================
root = tk.Tk()
root.title("자동 이미지 클릭기")
root.geometry("240x160")

status_label = tk.Label(root, text="상태: 실행 중")
status_label.pack(pady=8)

pause_btn = tk.Button(
    root,
    text="일시정지 / 재개 (F8)",
    command=toggle_pause,
    bg="#444",
    fg="white"
)
pause_btn.pack(pady=5)

stop_btn = tk.Button(
    root,
    text="종료 (ESC)",
    command=stop_program,
    bg="red",
    fg="white"
)
stop_btn.pack(pady=5)

threading.Thread(target=click_loop, daemon=True).start()
root.mainloop()
