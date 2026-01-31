from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from world.rows import ROWS
    from utils.types import SIZE, POS



from world.resources import Resource, Resources


class Warehouse:
    def __init__(self, rows:ROWS=None, pos:POS=None, size:SIZE=None) -> None:
        self.rows:ROWS = rows
        self.pos:POS = pos
        self.size:SIZE = size
        self.init()

    def init(self) -> None:
        self.cap:int = self.size[0] * self.size[1] * self.size[2] * 64
        self.rez: Resources = Resources()

    def total(self) -> int:
        return self.rez.total()

    def free(self) -> int:
        return self.cap - self.total()

    def fits(self, res:Resource=None) -> bool:
        if res is None:
            raise ValueError("[VALUE ERROR] Warehouse.fits(): res is None")
        res.validate()
        return self.free() >= res.amount
    
    def get(self, mat:str=None) -> Resource:
        if mat is None:
            raise ValueError("[VALUE ERROR] Warehouse.get(): mat is None")
        return self.rez.get(mat=mat)

    def has(self, res:Resource=None) -> tuple[Resource, Resource]:
        if res is None:
            raise ValueError("[VALUE ERROR] Warehouse.has(): res is None")
        res.validate()
        available = self.rez.rez.get(res.mat, Resource(mat=res.mat, amount=0)).copy()
        want = res.copy()
        return available, want
    
    def split(self, request:Resource=None) -> tuple[Resource, Resource]:
        if request is None:
            raise ValueError("[VALUE ERROR] Warehouse.split(): request is None")
        request.validate()
        requested, stock = self.get(mat=request.mat).split(value=request.amount) # part1 is what we give, part2 is what remains
        return requested, stock

    def give(self, incoming:Resource=None) -> Resource:
        if incoming is None:
            raise ValueError("[VALUE ERROR] Warehouse.give(): incoming is None")
        incoming.validate()
        give, notgive = incoming.split(value=self.free() if self.free() > 0 else 0)  # <-- unpack order matters!
        self.rez += give   # transfer stored into warehouse (stored becomes 0)
        return notgive      # what could NOT be stored

    def take(self, requested:Resource=None) -> Resource:
        if requested is None:
            raise ValueError("[VALUE ERROR] Warehouse.take(): requested is None")
        requested.validate()
        return self.split(request=requested)[0] # what we can provide