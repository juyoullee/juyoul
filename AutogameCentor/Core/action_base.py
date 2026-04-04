# Core/action_base.py

import time
import random
import pyautogui
import keyboard


class ActionsBase:

    def __init__(self):
        self.RUNNING = True

    # =====================================
    # 공통 제어
    # =====================================

    def esc_sleep(self, seconds):

        remaining = seconds

        while remaining > 0:

            if keyboard.is_pressed("esc"):
                print("ESC 중단")
                self.RUNNING = False
                return False

            time.sleep(0.05)
            remaining -= 0.05

        return True

    # =====================================
    # 기본 동작
    # =====================================

    def random_click(self, x, y, timer):

        if keyboard.is_pressed("esc"):
            print("ESC 중단")
            self.RUNNING = False
            return False

        rx = x + random.randint(-1, 1)
        ry = y + random.randint(-1, 1)

        pyautogui.click(rx, ry)

        return self.esc_sleep(timer)

    def random_moveto(self, x, y, timer):

        if keyboard.is_pressed("esc"):
            print("ESC 중단")
            self.RUNNING = False
            return False

        rx = x + random.randint(-1, 1)
        ry = y + random.randint(-1, 1)

        pyautogui.moveTo(rx, ry)

        return self.esc_sleep(timer)

    def random_drag(self, dx, dy, duration):

        rx = dx + random.randint(-10, 10)
        ry = dy + random.randint(-10, 10)

        pyautogui.dragRel(rx, ry, duration=duration)

        return True

    # =====================================
    # 단일 액션
    # =====================================

    def run_action(self, action, ax=0, ay=0):

        if not self.RUNNING:
            return False

        t = action[0]

        if t == "click":

            _, x, y, d = action
            return self.random_click(x + ax, y + ay, d)

        elif t == "move":

            _, x, y, d = action
            return self.random_moveto(x + ax, y + ay, d)

        elif t == "drag":

            _, dx, dy, d = action

            self.random_drag(dx, dy, d)

            return self.esc_sleep(d)

        elif t == "sleep":

            return self.esc_sleep(action[1])

        elif t == "key":

            pyautogui.press(action[1])

            return self.esc_sleep(action[2])

        elif t == "repeat":

            _, count, sub_action = action

            for _ in range(count):

                if not self.RUNNING:
                    return False

                result = self.run_action(sub_action, ax, ay)

                if result is False:
                    print("repeat 내부 종료")
                    continue

            return True

        else:

            raise ValueError(f"Unknown action type: {t}")

    # =====================================
    # 스크립트 실행 엔진
    # =====================================

    def run_actions(self, actions, ax=0, ay=0):

        # ★ 매 실행마다 상태 초기화
        self.RUNNING = True

        if isinstance(actions, dict):
            iterable = actions.items()
        else:
            iterable = enumerate(actions, start=1)

        for name, action in iterable:

            if not self.RUNNING:
                print("중단:", name)
                return False

            result = self.run_action(action, ax, ay)

            if result is False:
                print("중단:", name)
                return False

        return True

    def click_list(self, coords, ax=0, ay=0):

        self.RUNNING = True

        for x, y, delay in coords:
            if not self.random_click(x + ax, y + ay, delay):
                return False

        return True

    def run_with_offsets(self, actions, offsets):

        for ox, oy in offsets:
            if isinstance(actions, dict):
                if not self.run_actions(actions, ox, oy):
                    return False
            else:
                if not self.click_list(actions, ox, oy):
                    return False

        return True
