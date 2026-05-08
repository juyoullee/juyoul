import json
import os
import re
from copy import deepcopy

from Core.action_base import ActionsBase
from Core.action_specs import ActionSpec

WINDOW_LAYOUTS = {
    "l2m_9_grid": [
        (0, 0), (640, 0), (1280, 0),
        (0, 320), (640, 320), (1280, 320),
        (0, 623), (640, 623), (1280, 623),
    ]
}

WINDOW_RANGE_1 = [
    (0, 0), (640, 0), (1280, 0),
    (0, 320), (640, 320), (1280, 320),
    (0, 623), (640, 623), (1280, 623),
]


class RecordedActionLibrary(ActionsBase):

    def __init__(self, storage_path, open_creator, open_manager):
        super().__init__()
        self.storage_path = storage_path
        self.open_creator = open_creator
        self.open_manager = open_manager

    def get_action_specs(self):
        specs = [
            ActionSpec(
                id="macro.create",
                label="동작 추가",
                runner=self.open_creator,
                board="l2m_custom",
                countdown=0,
                background=False,
                minimize_gui=False,
            ),
            ActionSpec(
                id="macro.manage",
                label="동작 관리",
                runner=self.open_manager,
                board="l2m_custom",
                countdown=0,
                background=False,
                minimize_gui=False,
            ),
        ]

        for item in self.load_actions():
            specs.append(
                ActionSpec(
                    id=item["id"],
                    label=item["label"],
                    runner=self._make_runner(
                        item["steps"],
                        loop_count=int(item.get("loop_count", 1)),
                        loop_infinite=bool(item.get("loop_infinite", False)),
                        window_9grid=bool(item.get("window_9grid", False)),
                    ),
                    board=item.get("board", "l2m_custom"),
                    pre_focus=item.get("pre_focus") or "Lineage2M",
                    post_minimize=item.get("post_minimize"),
                    countdown=int(item.get("countdown", 3)),
                )
            )

        return specs

    def load_actions(self):
        if not os.path.exists(self.storage_path):
            return []

        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        actions = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            if not raw.get("id") or not raw.get("label") or not isinstance(raw.get("steps"), list):
                continue
            actions.append(raw)

        return actions

    def save_action(
        self,
        *,
        label,
        steps,
        board,
        pre_focus="Lineage2M",
        post_minimize=None,
        countdown=3,
        loop_count=1,
        loop_infinite=False,
        window_9grid=False,
    ):
        actions = self.load_actions()
        action_id = self._make_action_id(label, actions)
        actions.append(
            {
                "id": action_id,
                "label": label,
                "board": board,
                "pre_focus": pre_focus,
                "post_minimize": post_minimize,
                "countdown": countdown,
                "loop_count": max(1, int(loop_count)),
                "loop_infinite": bool(loop_infinite),
                "window_9grid": bool(window_9grid),
                "steps": deepcopy(steps),
            }
        )
        self._write_actions(actions)
        return action_id

    def get_action(self, action_id):
        for item in self.load_actions():
            if item.get("id") == action_id:
                return deepcopy(item)
        return None

    def update_action(
        self,
        action_id,
        *,
        label,
        steps,
        board,
        pre_focus="Lineage2M",
        post_minimize=None,
        countdown=3,
        loop_count=1,
        loop_infinite=False,
        window_9grid=False,
    ):
        actions = self.load_actions()

        for item in actions:
            if item.get("id") != action_id:
                continue
            item["label"] = label
            item["steps"] = deepcopy(steps)
            item["board"] = board
            item["pre_focus"] = pre_focus
            item["post_minimize"] = post_minimize
            item["countdown"] = countdown
            item["loop_count"] = max(1, int(loop_count))
            item["loop_infinite"] = bool(loop_infinite)
            item["window_9grid"] = bool(window_9grid)
            self._write_actions(actions)
            return True

        return False

    def delete_action(self, action_id):
        actions = self.load_actions()
        filtered = [item for item in actions if item.get("id") != action_id]
        if len(filtered) == len(actions):
            return False
        self._write_actions(filtered)
        return True

    def _write_actions(self, actions):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(actions, file, ensure_ascii=False, indent=2)

    def _make_runner(self, steps, loop_count=1, loop_infinite=False, window_9grid=False):
        frozen_steps = deepcopy(steps)
        total_loops = max(1, int(loop_count))
        repeat_forever = bool(loop_infinite)
        nine_grid = bool(window_9grid)

        def run():
            self.RUNNING = True
            executed = 0

            while self.RUNNING:
                offsets = WINDOW_RANGE_1 if nine_grid else [(0, 0)]
                for ox, oy in offsets:
                    for step in frozen_steps:
                        if not self._run_step(step, ox, oy):
                            return False

                executed += 1
                if not repeat_forever and executed >= total_loops:
                    break
            return True

        return run

    def _run_step(self, step, ox=0, oy=0):
        step_type = step.get("type")

        if step_type == "sleep":
            return self.esc_sleep(float(step.get("seconds", 0.0)))

        if step_type == "click":
            delay = float(step.get("delay", 0.0))
            if delay > 0:
                if not self.esc_sleep(delay):
                    return False
            return self.random_click(
                int(step["x"]) + ox,
                int(step["y"]) + oy,
                float(step.get("after", 0.05)),
            )

        if step_type == "drag":
            if not self.random_moveto(
                int(step["start_x"]) + ox,
                int(step["start_y"]) + oy,
                float(step.get("before", 0.05)),
            ):
                return False
            self.random_drag(
                int(step["delta_x"]),
                int(step["delta_y"]),
                float(step.get("duration", 0.2)),
            )
            return self.esc_sleep(float(step.get("after", 0.05)))

        if step_type == "repeat_click_pattern":
            count = int(step.get("count", 1))
            start_x = int(step["start_x"]) + ox
            start_y = int(step["start_y"]) + oy
            delta_x = int(step.get("delta_x", 0))
            delta_y = int(step.get("delta_y", 0))
            delay = float(step.get("after", 0.05))

            for index in range(count):
                x = start_x + (delta_x * index)
                y = start_y + (delta_y * index)
                if not self.random_click(x, y, delay):
                    return False
            return True

        if step_type == "window_grid_click":
            offsets = self._get_layout_offsets(step)
            base_x = int(step["base_x"]) + ox
            base_y = int(step["base_y"]) + oy
            delay = float(step.get("after", 0.05))

            for offset_x, offset_y in offsets:
                if not self.random_click(base_x + offset_x, base_y + offset_y, delay):
                    return False
            return True

        if step_type == "window_grid_drag":
            offsets = self._get_layout_offsets(step)
            base_x = int(step["base_x"]) + ox
            base_y = int(step["base_y"]) + oy
            delta_x = int(step["delta_x"])
            delta_y = int(step["delta_y"])
            before = float(step.get("before", 0.05))
            duration = float(step.get("duration", 0.2))
            after = float(step.get("after", 0.05))

            for offset_x, offset_y in offsets:
                if not self.random_moveto(base_x + offset_x, base_y + offset_y, before):
                    return False
                self.random_drag(delta_x, delta_y, duration)
                if not self.esc_sleep(after):
                    return False
            return True

        raise ValueError(f"Unsupported recorded step type: {step_type}")

    def _get_layout_offsets(self, step):
        layout_key = step.get("layout", "l2m_9_grid")
        return WINDOW_LAYOUTS.get(layout_key, WINDOW_LAYOUTS["l2m_9_grid"])

    def _make_action_id(self, label, existing):
        base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        if not base:
            base = "macro"

        used = {item["id"] for item in existing}
        candidate = f"macro.{base}"
        suffix = 2

        while candidate in used:
            candidate = f"macro.{base}_{suffix}"
            suffix += 1

        return candidate
