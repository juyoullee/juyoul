import pyautogui
import keyboard
import pyperclip
import time

print("===================================")
print("  좌표 복사기 실행됨")
print("  F8 누르면 현재 마우스 좌표 복사")
print("  ESC 누르면 종료")
print("===================================")

while True:
    if keyboard.is_pressed("esc"):
        print("종료")
        break

    if keyboard.is_pressed("f8"):
        x, y = pyautogui.position()
        coord = f"{x}, {y}"
        pyperclip.copy(coord)
        print("복사됨:", coord)
        time.sleep(0.3)   # 중복 입력 방지
