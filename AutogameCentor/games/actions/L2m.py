import datetime
import time

import keyboard

from Core.action_base import ActionsBase
from Core.action_specs import ActionSpec
from Core.window_control import bring_to_front, minimize_window
from games.Coordinates.L2m_coordi import L2mCoordinates


window_range_1 = [
    (0, 0), (640, 0), (1280, 0),
    (0, 320), (640, 320), (1280, 320),
    (0, 623), (640, 623), (1280, 623),
]


class L2mDayilyAction(ActionsBase):
    BASE_X = 320
    BASE_Y = 230

    button_methods = [
        "창불러오기", "창최소화", "절전모드","절전해제", "가방열기",
        "UL이벤트던전", "우편받기", "사냥터귀환", "경매장", "전체루틴",
        "이벤트제작", "UL정령계초기화", "시즌패스", "아이템강화",
        "UL데일리", "UL물약구매", "UL캐시상점", "너구리상점", "UL여포던전",
        "여포클릭", "고참상점","전체마을귀환"
    ]

    def get_action_specs(self):
        return [
            ActionSpec(id="l2m.focus", label="창불러오기", runner=self.창불러오기, board="l2m", countdown=1),
            ActionSpec(id="l2m.minimize", label="창최소화", runner=self.창최소화, board="l2m", countdown=1),
            ActionSpec(id="l2m.power_save", label="절전모드", runner=self.절전모드, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.bag_open", label="가방열기", runner=self.가방열기, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.event_dungeon", label="UL이벤트던전", runner=self.UL이벤트던전, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.mail", label="우편받기", runner=self.우편받기, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.return_hunt", label="사냥터귀환", runner=self.사냥터귀환, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.auction", label="경매장", runner=self.경매장, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.full_routine", label="전체루틴", runner=self.전체루틴, board="l2m", pre_focus="리니지2M", post_minimize="리니지2M"),
            ActionSpec(id="l2m.event_craft", label="이벤트제작", runner=self.이벤트제작, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.spirit_reset", label="UL정령계초기화", runner=self.UL정령계초기화, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.season_pass", label="시즌패스", runner=self.시즌패스, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.item_enchant", label="아이템강화", runner=self.아이템강화, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.daily", label="UL데일리", runner=self.UL데일리, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.potion", label="UL물약구매", runner=self.UL물약구매, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.cash_shop", label="UL캐시상점", runner=self.UL캐시상점, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.raccoon_shop", label="너구리상점", runner=self.너구리상점, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.yeopo_dungeon", label="여포던전", runner=self.여포던전, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.yeopo_click", label="여포클릭", runner=self.여포클릭, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.yeopo_shop", label="고참상점", runner=self.고참상점, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.power_save_off", label="절전해제", runner=self.절전해제, board="l2m", pre_focus="리니지2M"),
            ActionSpec(id="l2m.power_save_off", label="전체마을귀환", runner=self.전체마을귀환, board="l2m", pre_focus="리니지2M"),
        ]

    def _focus_and_reset(self, rx, ry):
        self.random_click(self.BASE_X + rx, self.BASE_Y + ry, 0.2)
        time.sleep(0.2)

    def _run_windows(self, actions):
        for idx, (rx, ry) in enumerate(window_range_1, 1):
            self._focus_and_reset(rx, ry)
            if not self.run_actions(actions, rx, ry):
                print(f"[FAIL] window={idx}")
                return False
        return True

    def 창불러오기(self):
        bring_to_front("리니지2M")
        return True

    def 창최소화(self):
        minimize_window("리니지2M")
        return True

    절전모드 = lambda self: self._run_windows(L2mCoordinates.절전모드)
    UL데일리 = lambda self: self._run_windows(L2mCoordinates.Dayily)
    UL물약구매 = lambda self: self._run_windows(L2mCoordinates.potion)
    UL캐시상점 = lambda self: self._run_windows(L2mCoordinates.cashShop)
    우편받기 = lambda self: self._run_windows(L2mCoordinates.우편받기)
    가방열기 = lambda self: self._run_windows(L2mCoordinates.가방열기)
    사냥터귀환 = lambda self: self._run_windows(L2mCoordinates.사냥터귀환)
    경매장 = lambda self: self._run_windows(L2mCoordinates.경매장)
    UL정령계초기화 = lambda self: self._run_windows(L2mCoordinates.정령계초기화)
    이벤트제작 = lambda self: self._run_windows(L2mCoordinates.이벤트제작)
    시즌패스 = lambda self: self._run_windows(L2mCoordinates.시즌패스)
    너구리상점 = lambda self: self._run_windows(L2mCoordinates.event_shop)
    UL이벤트던전 = lambda self: self._run_windows(L2mCoordinates.EventDungeon)
    여포던전 = lambda self: self._run_windows(L2mCoordinates.이벤트던전_여포)
    고참상점 = lambda self: self._run_windows(L2mCoordinates.고참상점)
    절전해제 = lambda self: self._run_windows(L2mCoordinates.절전해제)
    전체마을귀환 = lambda self: self._run_windows(L2mCoordinates.전체마을귀환)

    def 전체루틴(self):
        for fn in [self.UL데일리, self.UL물약구매, self.UL캐시상점, self.창최소화]:
            if not fn():
                return False
        return True

    def 아이템강화(self):
        for part in L2mCoordinates.아이템강화.values():
            for rx, ry in window_range_1:
                self._focus_and_reset(rx, ry)
                if not self.run_actions(part, rx, ry):
                    return False
        return True

    def 여포클릭(self):
        while True:
            if keyboard.is_pressed("esc"):
                break

            for rx, ry in window_range_1:
                if keyboard.is_pressed("esc"):
                    break

                self.random_click(483 + rx, 186 + ry, 0.1)
                self.random_click(483 + rx, 186 + ry, 0.1)

                end = time.time() + 0.3
                while time.time() < end:
                    if keyboard.is_pressed("esc"):
                        break
                    time.sleep(0.01)

        return True


class L2mDayDungeonAction(ActionsBase):
    BASE_X = 320
    BASE_Y = 230

    button_methods = ["L2M요일던전"]

    def get_action_specs(self):
        return [
            ActionSpec(
                id="l2m.day_dungeon",
                label="L2M요일던전",
                runner=self.L2M요일던전,
                board="l2m_dungeon",
                pre_focus="리니지2M",
            ),
        ]

    def _focus_and_reset(self, rx, ry):
        self.random_click(self.BASE_X + rx, self.BASE_Y + ry, 0.2)
        time.sleep(0.2)

    def L2M요일던전(self):
        weekday = datetime.datetime.today().weekday()

        for idx, (ax, ay) in enumerate(window_range_1, 1):
            self._focus_and_reset(ax, ay)

            if not self.run_actions(L2mCoordinates.DAY_DUNGEON[weekday], ax, ay):
                print(f"[FAIL] window={idx}, dungeon")
                return False

            if not self.run_actions(L2mCoordinates.Day_AFTER_ENTER, ax, ay):
                print(f"[FAIL] window={idx}, after")
                return False

        return True
