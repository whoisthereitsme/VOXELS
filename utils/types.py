from typing import TypeAlias
from numpy.typing import NDArray
import numpy as np

POS: TypeAlias = tuple[int, int, int]
SIZE: TypeAlias = tuple[int, int, int]
NDARR = NDArray[np.uint64]
REQS = tuple[NDARR, dict[int, int]]

__all__ = [
    "POS",
    "SIZE",
    "NDARR",
    "REQS",
]
