from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    pass

from .resource import Resource, RESOURCELIKE    


class Resources:
    def __init__(self, rez:RESOURCELIKE=None) -> None:
        self.rez: dict[str, Resource] = {}
        self.ingest(rez=rez)

    def tolist(self, rez:RESOURCELIKE=None) -> list[Resource]:
        if rez is None:
            return self.list()

        if isinstance(rez, Resource):
            return [rez]

        if isinstance(rez, Resources):
            return rez.list()

        if isinstance(rez, list):
            return rez

        if isinstance(rez, tuple):
            return list(rez)

        if isinstance(rez, set):
            return list(rez)

        if isinstance(rez, dict):
            # copy values into new Resources (do NOT mutate originals)
            return [Resource(mat=r.mat, amount=r.amount) for r in rez.values()]

        raise ValueError(f"[VALUE ERROR] Resources.tolist(): invalid type: {type(rez)}")

    def get(self, mat:str=None) -> Resource:
        if mat is None:
            raise ValueError("[VALUE ERROR] Resources.get(): mat is None")
        if mat not in self.rez:
            self.rez[mat] = Resource(mat=mat, amount=0)
        return self.rez[mat]

    def ingest(self, rez:RESOURCELIKE=None) -> None:
        for r in self.tolist(rez=rez):
            r.validate()
            cur = self.get(mat=r.mat)
            cur + r  # mutates cur only; r unchanged

    def transfer(self, rez:RESOURCELIKE=None) -> None:
        for r in self.tolist(rez=rez):
            r.validate()
            cur = self.get(mat=r.mat)
            cur += r  # transfer; r becomes 0

    def total(self) -> int:
        total = 0
        for r in self.tolist():
            total += r.amount
        return total

    def list(self) -> list[Resource]:
        return list(self.rez.values())

    def copy(self) -> Resources:
        return Resources(rez=[r.copy() for r in self.tolist()])

    def __copy__(self) -> Resources:
        return self.copy()

    def __deepcopy__(self, memo) -> Resources:
        return self.copy()

    # ------------------------------------------------------------
    # Semantics requested (for containers):
    #
    # a + b  : b does NOT mutate, a DOES mutate (adds)
    # a += b : transfer; a increases, b becomes 0 (per material)
    #
    # a - b  : b does NOT mutate, a DOES mutate (subtract up to b.amount)
    # a -= b : transfer-like; a decreases, b becomes remaining demand
    # ------------------------------------------------------------

    def __add__(self, other:RESOURCELIKE=None) -> Resources:
        self.ingest(rez=other)
        return self

    def __iadd__(self, other:RESOURCELIKE=None) -> Resources:
        self.transfer(rez=other)
        return self

    def __sub__(self, other:RESOURCELIKE=None) -> Resources:
        for r in self.tolist(rez=other):
            r.validate()
            cur = self.get(mat=r.mat)
            cur - r  # mutates cur only; r unchanged
        return self

    def __isub__(self, other:RESOURCELIKE=None) -> Resources:
        for r in self.tolist(rez=other):
            r.validate()
            cur = self.get(mat=r.mat)
            cur -= r  # mutates both: cur decreases, r becomes remaining demand
        return self

    def __bool__(self) -> bool:
        for r in self.list():
            bool(r)
        return True

    def __repr__(self) -> str:
        return f"Resources({self.list()})"

    def __str__(self) -> str:
        return self.__repr__()
