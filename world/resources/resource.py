from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from.resources import Resources





RESOURCELIKE: TypeAlias = "Resource | Resources | list[Resource] | tuple[Resource, ...] | set[Resource] | dict[str, Resource] | None"


class Resource:
    def __init__(self, mat:str=None, amount:int=0) -> None:
        self.mat:str = mat
        self.amount:int = amount
        self.validate()

    def validate(self) -> Resource:
        if self.mat is None:
            raise ValueError("[VALUE ERROR] Resource.validate(): mat is None")
        if self.amount < 0:
            raise ValueError(f"[VALUE ERROR] Resource.validate(): amount out of bounds: {self.amount}")
        return self

    def compatible(self, other:Resource=None) -> bool:
        if isinstance(other, Resource):
            self.validate()
            other.validate()
            if self.mat == other.mat:
                return True
        raise ValueError(f"[VALUE ERROR] Resource.compatible(): incompatible resources: {self} vs {other}")

    def copy(self) -> Resource:
        return Resource(mat=self.mat, amount=self.amount)

    def __copy__(self) -> Resource:
        return self.copy()

    def __deepcopy__(self, memo) -> Resource:
        return self.copy()

    # ------------------------------------------------------------
    # Semantics requested:
    #
    # a + b  : b does NOT mutate, a DOES mutate (adds b.amount)
    # a += b : transfer; a increases, b becomes 0
    #
    # a - b  : b does NOT mutate, a DOES mutate (subtract up to b.amount)
    # a -= b : transfer-like; a decreases, b becomes "remaining" demand
    #          (b ends up 0 if a had enough, else b keeps leftover)
    # ------------------------------------------------------------

    def __add__(self, other:Resource=None) -> Resource:
        if self.compatible(other=other):
            self.amount += other.amount
        return self.validate()

    def __iadd__(self, other:Resource=None) -> Resource:
        if self.compatible(other=other):
            self.amount += other.amount
            other.amount = 0
            other.validate()
        return self.validate()

    def __sub__(self, other:Resource=None) -> Resource:
        if self.compatible(other=other):
            take = other.amount
            if self.amount < take:
                take = self.amount
            self.amount -= take
        return self.validate()

    def __isub__(self, other:Resource=None) -> Resource:
        if self.compatible(other=other):
            take = other.amount
            if self.amount < take:
                take = self.amount
            self.amount -= take
            other.amount -= take
            other.validate()
        return self.validate()

    # ---------------- comparisons (same-material only) ----------------

    def __lt__(self, other:Resource=None) -> bool:
        if self.compatible(other=other):
            return self.amount < other.amount
        return False

    def __le__(self, other:Resource=None) -> bool:
        if self.compatible(other=other):
            return self.amount <= other.amount
        return False

    def __gt__(self, other:Resource=None) -> bool:
        if self.compatible(other=other):
            return self.amount > other.amount
        return False

    def __ge__(self, other:Resource=None) -> bool:
        if self.compatible(other=other):
            return self.amount >= other.amount
        return False

    def __eq__(self, other:object=None) -> bool:
        if not isinstance(other, Resource):
            return False
        if self.mat != other.mat:
            return False
        return self.amount == other.amount

    def __ne__(self, other:object=None) -> bool:
        return not self.__eq__(other)

    # ---------------- misc ----------------

    def __int__(self) -> int:
        return self.amount

    def __bool__(self) -> bool:
        self.validate()
        return True

    def __repr__(self) -> str:
        return f"Resource(mat={self.mat}, amount={self.amount})"

    def __str__(self) -> str:
        return self.__repr__()

    def sort(self, others:list[Resource]=None, reverse:bool=False) -> list[Resource]:
        if others is None:
            others = []
        for o in others:
            self.compatible(other=o)
        return sorted([self] + others, reverse=reverse)

    def split(self, value:int=None) -> list[Resource]:
        self.validate()
        if value is None or value < 0:
            raise ValueError(f"[VALUE ERROR] Resource.split(): invalid split value: {value}")

        take = min(value, self.amount)
        part1 = Resource(mat=self.mat, amount=take)
        self = self - part1
        return [part1, self]   # [before split, after split]
    