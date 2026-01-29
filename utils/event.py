from __future__ import annotations
from typing import Any, Callable
from dataclasses import dataclass, field
from .event import Event
from .schedule import Schedule



@dataclass(order=True)
class Event:
    due_ns: int
    seq: int
    callback: Callable[..., Any] = field(compare=False)
    args: tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict[str, Any] = field(default_factory=dict, compare=False)
    cancelled: bool = field(default=False, compare=False)


class Handler:
    __slots__ = ("_scheduler", "_event")

    def __init__(self, scheduler: "Schedule", event: Event) -> None:
        self._scheduler = scheduler
        self._event = event

    def cancel(self) -> bool:
        return self._scheduler.cancel(self)

