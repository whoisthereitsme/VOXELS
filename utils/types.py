from typing import TypeAlias
from numpy.typing import NDArray
import numpy as np

POS: TypeAlias = tuple[int, int, int]
SIZE: TypeAlias = tuple[int, int, int]
NDARR = NDArray[np.uint64]
REQS = tuple[NDARR, dict[int, int]]

from dataclasses import dataclass
@dataclass(slots=True)
class Row:
    mid: int
    rid: int
    row: NDARR

__all__ = [
    "POS",
    "SIZE",
    "NDARR",
    "REQS",
    "Row",
]
