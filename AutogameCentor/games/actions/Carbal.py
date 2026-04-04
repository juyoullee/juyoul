import sys
import os
from datetime import datetime
import time
import random

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../")
)

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from Core.action_base import ActionsBase
from Core.action_specs import ActionSpec


class CarbalRed(ActionsBase):

    # ===============================
    # 좌표
    # ===============================

    def Daily_Coordi(self):

        return {

            "창으로이동": ("click", 479, 285, 0.5),
            "절전해제": ("drag", -300, 0, 0.5),
            "대기시간": ("sleep", 5),

            # 길드
            "길드_메뉴": ("click", 932, 60, 1.5),
            "길드_길드창": ("click", 788, 344, 1.5),
            "길드_보상수령": ("click", 438, 460, 1.5),
            "길드_보상수령2": ("click", 478, 435, 2),
            "길드_보상수령3": ("click", 478, 435, 2),
            "길드_길드기부": ("click", 915, 444, 1.5),
            "길드_길드기부_max": ("click", 437, 316, 1.5),
            "길드_길드기부_확인": ("click", 379, 445, 1.5),
            "길드_길드기부_확인_2": ("click", 379, 445, 1.5),
            "길드_길드기부닫기": ("click", 685, 71, 1),
            "길드_길드창닫기": ("click", 941, 51, 1.5),

            # 우정
            "우정_메뉴": ("click", 932, 60, 1.5),
            "우정_친구": ("click", 851, 347, 1.5),
            "우정_모두보내기": ("click", 904, 490, 1.5),
            "우정_모두받기": ("click", 808, 490, 1.5),
            "우정_친구창닫기": ("click", 941, 51, 1.5),
            "우정_캐시상점": ("click", 845, 61, 1.5),
            "우정_상점전체보기": ("click", 62, 476, 1.5),
            "우정_구매확인": ("click", 544, 463, 2),
            "우정_구매확인_2": ("click", 544, 463, 1.5),
            "우정_닫기": ("click", 941, 51, 1.5),

            # 우편
            "우편_메뉴": ("click", 932, 60, 1),
            "우편_우편": ("click", 662, 474, 1.5),
            "우편_서버우편": ("click", 250, 85, 0.5),
            "우편_모두받기": ("click", 906, 490, 0.5),
            "우편_모두받기확인": ("repeat", 2, ("click", 906, 490, 0.5)),
            "우편_닫기": ("click", 941, 51, 1.5),

            # 시즌패스
            "시즌패스_메뉴": ("click", 932, 60, 1),
            "시즌패스_시즌패스1": ("click", 659, 403, 1),
            "시즌패스_모두받기": ("repeat", 4, ("click", 890, 489, 0.5)),
            "시즌패스_시즌패스2": ("click", 293, 92, 1.5),
            "시즌패스_모두받기2": ("repeat", 4, ("click", 890, 489, 0.5)),
            "시즌패스_닫기": ("click", 941, 51, 1),

            # 업적
            "업적_메뉴": ("click", 932, 60, 1),
            "업적_업적": ("click", 724, 343, 1),
            "업적_모두받기확인": ("repeat", 3, ("click", 906, 490, 0.5)),
            "업적_닫기": ("click", 941, 51, 1),

            # 미션
            "미션_메뉴": ("click", 932, 60, 1),
            "미션_미션": ("click", 851, 233, 1),
            "미션_일일모두받기확인": ("repeat", 3, ("click", 906, 490, 0.5)),
            "미션_주간탭": ("click", 153, 88, 1),
            "미션_주간모두받기확인": ("repeat", 3, ("click", 906, 490, 0.5)),
            "미션_닫기": ("click", 942, 53, 1.5),}

    def Potion_Coordi(self):

        return {

            "창으로이동": ("click", 479, 285, 0.5),
            "절전해제": ("drag", -300, 0, 0.5),
            "대기시간": ("sleep", 5),

            "원격_메뉴": ("click", 753, 65, 1),
            "원격_상점": ("click", 755, 140, 1),
            "원격_중급물약": ("click", 156, 163, 1),
            "원격_MAX": ("click", 636, 349, 1),
            "원격_구매확인": ("click", 542, 406, 1),
            "원격_닫기": ("click", 907, 48, 1),
            "원격_절전": ("click", 23, 383, 1),
        }

    # ===============================
    # 공통 실행
    # ===============================

    def run_offsets(self, actions, offsets=(0, 515)):

        return self.run_with_offsets(actions, tuple((0, ay) for ay in offsets))

    def get_action_specs(self):
        return [
            ActionSpec(
                id="carbal.daily",
                label="데일리",
                runner=self.데일리,
                board="carbal",
                pre_focus="CARBAL",
                post_minimize="CARBAL",
            ),
            ActionSpec(
                id="carbal.potion",
                label="물약",
                runner=self.물약,
                board="carbal",
                pre_focus="CARBAL",
            ),
        ]

    # ===============================
    # 매크로
    # ===============================

    def 데일리(self):
        return self.run_offsets(self.Daily_Coordi())

    def 물약(self):

        actions = self.Potion_Coordi()

        while True:
            if not self.run_offsets(actions):
                return False
            time.sleep(random.randint(900, 1200))




if __name__ == "__main__":
    CarbalRed().물약()
