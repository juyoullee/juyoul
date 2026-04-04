from Core.action_base import ActionsBase
from Core.action_specs import ActionSpec
from Core.window_control import bring_to_front, minimize_window
from games.actions.filters import filter_shadow
from UI.dialogs import ask_shadow_shop
import time

# ============================================================
# Coordinates
# ============================================================

class OdinCoordinates:
    def Daily_Coordi(self):
        return {
            "창으로이동": ("move", 1438, 250, 0.5),
            "절전해제": ("drag", -368, 0, 0.5),
            "대기시간": ("sleep", 10),
            "메뉴": ("click", 1885, 52, 1),
            "길드": ("click", 1626, 324, 4),
            "길드확인": ("click", 1626, 324, 1),
            "길드정보탭": ("click", 1131, 93, 0.6),
            "기부": ("repeat", 10, ("click", 1460, 480, 0.2)),
            "길드닫기": ("click", 1898, 51, 1.5),
            "가방": ("click", 1835, 53, 3),
            "일괄분해": ("click", 1654, 488, 0.5),
            "분해": ("click", 1863, 488, 0.5),
            "분해확인": ("click", 1498, 381, 10),
            "분해확인클릭": ("click", 1447, 478, 1),
            "분해해닫기": ("click", 1897, 51, 1.5),
            "메뉴2": ("click", 1885, 52, 1),
            "우편": ("click", 1676, 462, 2.5),
            "우편받기": ("repeat", 4, ("click", 1853, 492, 1)),
            "계정탭": ("click", 1164, 95, 1),
            "계정우편받기": ("repeat", 4, ("click", 1853, 492, 1)),
            "우편닫기": ("click", 1897, 51, 1.5),
            "상점": ("click", 1783, 53, 3),
            "일괄구매": ("click", 1029, 419, 1),
            "구매확인": ("click", 1513, 417, 2.5),
            "구매확인_2": ("click", 1029, 419, 1),
            "상점닫기": ("click", 1899, 52, 1),
            "스케줄러": ("click", 986, 191, 1),
            "상세": ("click", 1736, 234, 0.4),
            "상세확인": ("click", 1440, 445, 0.4),
            "상세확인2": ("click", 1439, 419, 0.4),
            "사용체크": ("click", 1107, 230, 0.4),
            "시작하기": ("click", 1501, 472, 0.4),
        }

    def 지하감옥입장(self):
        return {
            "0.창으로이동": ("move", 1368, 316, 0.5),
            "1.절전해제": ("drag", -368, 0, 0.5),
            "2.대기시간": ("sleep", 5),
            "3.메뉴": ("click", 1873, 59, 1),
            "4.던전": ("click", 1605, 417, 1.5),
            "5.정예던전탭": ("click", 1088, 111, 1),
            "6.좌표이동": ("move", 1854, 317, 1),
            "7.던전드래그": ("drag", -1000, 0, 0.3),
            "6.좌표이동": ("move", 1854, 317, 1),
            "7.던전드래그": ("drag", -1000, 0, 0.3),
            "8.지하감옥클릭": ("click", 1723, 317, 1),
            "9.8단계 클릭": ("click", 961, 581, 1),
            "10.이동": ("click", 1777, 610, 20),
            "11.순간이동": ("click", 1486, 602, 7),
            "12.자동사냥": ("click", 1855, 491, 0.5),
            "13.절전": ("click", 854, 425, 1),
        }

    def 그림자성채입장(self):
        return {
            "0.창으로이동": ("move", 1368, 316, 0.5),
            "1.절전해제": ("drag", -368, 0, 0.5),
            "2.대기시간": ("sleep", 5),
            "3.메뉴": ("click", 1873, 59, 1),
            "4.던전": ("click", 1605, 417, 1.5),
            "5.정예던전탭": ("click", 1088, 111, 1),
            "6.3번째가 성채일때": ("click", 1742, 314, 2),
            "7.그림자성채상점클릭": ("click", 1260, 620, 3),
            "8_1.물약구매": ("click", 1002, 219, 0.7),
            "8_2.물약구매": ("click", 1367, 410, 0.7),
            "8_3.물약구매": ("click", 1448, 521, 0.7),
            "9_1.주문서구매": ("click", 1011, 311, 0.7),
            "9_2.주문서구매": ("click", 1367, 410, 0.7),
            "9_3.주문서구매": ("click", 1448, 521, 0.7),
            "10.상점닫기": ("click", 855, 60, 2),
            "11.3단계선택": ("click", 969, 257, 1),
            "12.입장": ("click", 1780, 550, 1),
        }

    def Daily_Macro(self):
        return {
            "창으로이동": ("move", 1368, 316, 0.5),
            "절전해제": ("drag", -368, 0, 0.5),
            "대기시간": ("sleep", 10),
            "스케줄러": ("click", 855, 241, 1),
            "상세": ("click", 1751, 294, 0.4),
            "상세확인": ("click", 1369, 575, 0.4),
            "상세확인2": ("click", 1368, 535, 0.4),
            "확인": ("click", 934, 293, 0.4),
            "스케줄시작": ("click", 1450, 608, 20),
            "절전": ("click", 854, 428, 1),        }


# ============================================================
# Actions
# ============================================================

class Odin_Action(ActionsBase):
    def __init__(self):
        super().__init__()
        self.coord = OdinCoordinates()

    def get_action_specs(self):
        return [
            ActionSpec(
                id="odin.focus",
                label="창 불러오기",
                runner=self.창불러오기,
                board="odin",
                pre_focus=None,
                post_minimize=None,
                countdown=1,
            ),
            ActionSpec(
                id="odin.minimize",
                label="창 최소화",
                runner=self.창최소화,
                board="odin",
                countdown=1,
            ),
            ActionSpec(
                id="odin.daily",
                label="오딘 데일리",
                runner=self.오딘데일리,
                board="odin",
                pre_focus="ODIN",
                post_minimize="ODIN",
            ),
            ActionSpec(
                id="odin.dungeon.floor8",
                label="지하감옥 8단계",
                runner=self.지하감옥8단계,
                board="odin",
                pre_focus="ODIN",
            ),
            ActionSpec(
                id="odin.shadow_castle",
                label="그림자 성채",
                runner=self.그림자성채,
                board="odin",
                pre_focus="ODIN",
            ),
            ActionSpec(
                id="odin.account_farm",
                label="계정 파던",
                runner=self.계정파던,
                board="odin",
                pre_focus="ODIN",
            ),
        ]

    def 오딘데일리(self):
        y_offsets = ((0, 0), (0, 516))
        actions = self.coord.Daily_Coordi()

        if not self.run_with_offsets(actions, y_offsets):
            return False

        minimize_window("ODIN")
        return True

    def 지하감옥8단계(self):
        y_offsets = ((0, 0), (0, 365))
        actions = self.coord.지하감옥입장()
        return self.run_with_offsets(actions, y_offsets)

    def 그림자성채(self):
        y_offsets = ((0, 0), (0, 365))
        actions = self.coord.그림자성채입장()

        use_shop = ask_shadow_shop()
        run_list = filter_shadow(actions, use_shop)
        return self.run_with_offsets(run_list, y_offsets)

    def 창불러오기(self):
        bring_to_front("ODIN")

    def 창최소화(self):
        minimize_window("ODIN")

    def 데일리_매크로(self):
        y_offsets = ((0, 0), (0, 365))
        actions = self.coord.Daily_Macro()

        if not self.run_with_offsets(actions, y_offsets):
            return False

        minimize_window("ODIN")
        return True


    def 계정파던(self):
        self.random_click(4328, 925, 0.5)
        self.random_click(3850, 1066, 0.5)
        self.random_click(4341, 437, 0.5)
        self.random_click(3850, 580, 0.5)
        self.random_click(1804, 685, 0.5)
        self.random_click(1447, 796, 0.5)
        self.random_click(1809, 325, 0.5)
        self.random_click(1443, 433, 0.5)
        return True
