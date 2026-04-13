from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ActionSpec:
    id: str
    label: str
    runner: Callable[[], bool | None]
    board: str
    pre_focus: str | None = None
    post_minimize: str | None = None
    countdown: int = 3
    enabled: bool = True
    background: bool = True
    minimize_gui: bool = True


@dataclass(frozen=True)
class BoardSpec:
    id: str
    title: str
    columns: int = 4
    button_width: int = 14


@dataclass(frozen=True)
class AppSection:
    board: BoardSpec
    actions: list[ActionSpec] = field(default_factory=list)
