from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


import numpy as np
from numpy.typing import NDArray

from world.row import ROW
from utils.bvh import BVH
from world.materials import Materials, MATERIALS
from utils.types import POS, SIZE





class ROWS:
    SIZE = 65536

    def __init__(self) -> None:
        self.size = ROWS.SIZE
        self.mats = Materials()
        self.bvh = BVH(rows=self)
        # n is a dict of n
        self.n:dict[int, int] = {mid: 0 for mid in range(MATERIALS.NUM)}  # number of valid rows per material
        self.m = 0  # for the total number of rows used

        self.array: NDArray[ROW.DTYPE] = np.full((MATERIALS.NUM, self.size, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE)
        self.shape = self.array.shape
        self.nbytes = self.array.nbytes
        self.gbytes = self.nbytes / (1024**3)

        mat = "STONE"
        self.append(p0=(ROW.XMIN, ROW.YMIN, ROW.ZMIN), p1=(ROW.XMAX, ROW.YMAX, ROW.ZMAX), mat=mat)  # alive and dirty by default are true so no need to specify : easier to use now!!!


    def newn(self, mat:str=None) -> int:
        mid: int = MATERIALS.IDX[mat]
        n: int = self.n[mid]
        self.n[mid] += 1
        self.m += 1
        return n
    
    def deln(self, mat: str=None) -> int:
        if mat is None:
            raise ValueError("material must be specified")
        mid = MATERIALS.IDX[mat]
        if self.n[mid] <= 0:
            raise ValueError("no rows to free")
        self.n[mid] -= 1
        self.m -= 1
        return self.n[mid]
            

    def append(self, p0:POS=None, p1:POS=None, mat:str=None, dirty:bool=True, alive:bool=True) -> ROWS:
        matid: int = MATERIALS.IDX[mat]
        rid: int = self.newn(mat=mat)
        self.array[matid][rid] = ROW.new(p0=p0, p1=p1, mat=mat, rid=rid, dirty=dirty, alive=alive) # added rid=n so that bvh can use it when i provide a row as argument
        self.bvh.insert(mat=mat, rid=rid)  # insert into bvh index
        return self
    
    def delete(self, index: int, mat: str) -> ROWS:
        matid = MATERIALS.IDX[mat]
        n = self.n[matid]
        if index < 0 or index >= n:
            raise IndexError("index out of range")
        last = n - 1
        self.bvh.remove(mat=mat, rid=index)

        if index != last:
            self.bvh.remove(mat=mat, rid=last)
            self.array[matid][index] = self.array[matid][last]
            self.array[matid][index][*ROW.ID] = np.uint64(index)
            self.bvh.insert(mat=mat, rid=index)

        self.array[matid][last] = ROW.ARRAY
        self.deln(mat=mat)
        return self
    

    def find(self, pos:POS=None) -> tuple[str, int, NDArray[ROW.DTYPE]]:
        mat, rid, row = self.bvh.find(pos=pos)
        return (mat, rid, row)
    
    def get(self, mat:str=None, rid:int=None) -> NDArray[ROW.DTYPE]:
        return self.array[MATERIALS.IDX[mat]][rid]

    def nrows(self, mat:str=None) -> int:
        return self.n[MATERIALS.IDX[mat]]
    

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        n = self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"





rows = ROWS()
