from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.rows import ROWS









class Miner:
    def __init__(self, rows:ROWS=None) -> None:
        self.rows: ROWS = rows