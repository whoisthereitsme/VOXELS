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
from utils.mdx import MDX




class ROWS:
    SIZE = 65536
    def __init__(self) -> None:
        self.mats = Materials()
        self.bvh = BVH(rows=self)
        self.mdx = MDX(rows=self)
        self.n:dict[int, int] = {mid: 0 for mid in range(MATERIALS.NUM)}  # number of valid rows per material
        self.m = 0  # for the total number of rows used

        self.array: NDArray[ROW.DTYPE] = np.full((MATERIALS.NUM, ROWS.SIZE, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE)
        self.shape = self.array.shape
        self.nbytes = self.array.nbytes
        self.gbytes = self.nbytes / (1024**3)

        mat = "STONE"
        self.insert(p0=(ROW.XMIN, ROW.YMIN, ROW.ZMIN), p1=(ROW.XMAX, ROW.YMAX, ROW.ZMAX), mat=mat)  # alive and dirty by default are true so no need to specify : easier to use now!!!
        self.size = ROW.XMAX - ROW.XMIN, ROW.YMAX - ROW.YMIN, ROW.ZMAX - ROW.ZMIN

    def newn(self, mat:str=None) -> int:
        mid: int = Materials.name2idx[mat]
        n: int = self.n[mid]
        self.n[mid] += 1
        self.m += 1
        return n
    
    def deln(self, mat: str=None) -> int:
        if mat is None:
            raise ValueError("material must be specified")
        mid = Materials.name2idx[mat]
        if self.n[mid] <= 0:
            raise ValueError("no rows to free")
        self.n[mid] -= 1
        self.m -= 1
        return self.n[mid]
            
    def insert(self, p0:POS=None, p1:POS=None, mat:str=None, dirty:bool=True, alive:bool=True) -> ROWS:
        mid: int = Materials.name2idx[mat]
        rid: int = self.newn(mat=mat)
        row = ROW.new(p0=p0, p1=p1, mat=mat, rid=rid, dirty=dirty, alive=alive)
        self.array[mid][rid] = row  # added rid=n so that bvh can use it when i provide a row as argument
        self.bvh.insert(row=row)  # insert into bvh index
        self.mdx.insert(row=row)
        return self
    
    def remove(self, index:int=None, mat:str=None, row:NDArray[ROW.DTYPE]=None) -> ROWS:
        if row is not None and index is None and mat is None:
            mat = ROW.MAT(row=row)
            index = ROW.RID(row=row)
        mid = Materials.name2idx[mat]
        n = self.n[mid]
        if index < 0 or index >= n:
            raise IndexError("index out of range")
        last = n - 1
        self.bvh.remove(mat=mat, rid=index)
        self.mdx.remove(mat=mat, rid=index)

        if index != last:
            self.bvh.remove(mat=mat, rid=last)
            self.mdx.remove(mat=mat, rid=last)
            self.array[mid][index] = self.array[mid][last]
            self.array[mid][index][*ROW.IDS_ID] = np.uint64(index)
            self.bvh.insert(row=self.array[mid][index])
            self.mdx.insert(row=self.array[mid][index])

        self.array[mid][last] = ROW.ARRAY
        self.deln(mat=mat)
        return self
    
    def volume(self) -> int:
        total = 0
        for mid in range(MATERIALS.NUM):
            n = self.n[mid]
            for rid in range(n):
                row = self.array[mid][rid]
                total += ROW.VOLUME(row=row)
        return total

    def find(self, pos:POS=None) -> tuple[str, int, NDArray[ROW.DTYPE]]:
        mat, rid, row = self.bvh.find(pos=pos)
        return (mat, rid, row)
    
    def get(self, mat:str=None, rid:int=None) -> NDArray[ROW.DTYPE]:
        return self.array[Materials.name2idx[mat]][rid]

    def nrows(self, mat:str=None) -> int:
        return self.n[Materials.name2idx[mat]]
    
    def split(self, pos:POS=None, mat:str=None) -> tuple[int, int]:
        mat0, rid, row = self.find(pos=pos)
        p0 = ROW.P0(row=row)
        p1 = ROW.P1(row=row)
        
        x0, y0, z0 = p0
        x1, y1, z1 = pos
        x2, y2, z2 =x1+1, y1+1, z1+1
        x3, y3, z3 = p1

        xs = [[x0, x1], [x1, x2], [x2, x3]]
        ys = [[y0, y1], [y1, y2], [y2, y3]]
        zs = [[z0, z1], [z1, z2], [z2, z3]]

        for i, (X0, X1) in enumerate(xs):
            for j, (Y0, Y1) in enumerate(ys):
                for k, (Z0, Z1) in enumerate(zs):
                    size = (X1 - X0) * (Y1 - Y0) * (Z1 - Z0)
                    if size > 0:
                        if i == 1 and j == 1 and k == 1:    # the center cube should get the new material (its the one containing pos)
                            self.insert(p0=(X0, Y0, Z0), p1=(X1, Y1, Z1), mat=mat) # use new the material given for the new row
                        else:
                            self.insert(p0=(X0, Y0, Z0), p1=(X1, Y1, Z1), mat=mat0) # use the old material for the other rows

        self.remove(row=row)  # remove the original row



    def merge_pair(self, mat: str, rid_a: int, rid_b: int) -> bool:
        mid = Materials.name2idx[mat]
        n = self.n[mid]
        if rid_a < 0 or rid_a >= n or rid_b < 0 or rid_b >= n or rid_a == rid_b:
            return False

        row_a = self.array[mid][rid_a]
        row_b = self.array[mid][rid_b]

        touch = ROW.MERGE(row0=row_a, row1=row_b)
        if touch == (False, False, False):
            return False

        # merged bounds
        p0 = ROW.SORT(p0=ROW.P0(row=row_a), p1=ROW.P0(row=row_b))[0]
        p1 = ROW.SORT(p0=ROW.P1(row=row_a), p1=ROW.P1(row=row_b))[1]

        # remove higher rid first (because remove() swap-deletes)
        hi = rid_a if rid_a > rid_b else rid_b
        lo = rid_b if hi == rid_a else rid_a
        self.remove(mat=mat, index=hi)
        self.remove(mat=mat, index=lo)

        self.insert(p0=p0, p1=p1, mat=mat)
        return True

    def merge_pass(self, mat: str, axis: int) -> int:
        mid = Materials.name2idx[mat]
        merges = 0

        rid = 0
        while rid < self.n[mid]:
            partner = self.mdx.find_partner(mid=mid, rid=rid, axis=axis)
            if partner is None:
                rid += 1
                continue

            _, rid2 = partner
            if self.merge_pair(mat=mat, rid_a=rid, rid_b=rid2):
                merges += 1
                # don't increment rid: slot now contains swapped-in row
            else:
                rid += 1

        return merges
    
    def merge(self, mat:str=None) -> int:
        total = 0
        while True:
            m = (
                self.merge_pass(mat, axis=self.mdx.AX_X) +
                self.merge_pass(mat, axis=self.mdx.AX_Y) +
                self.merge_pass(mat, axis=self.mdx.AX_Z)
            )
            total += m
            if m == 0:
                return total
            
    def sweep(self) -> int:
        for mat in self.mats.name2idx.keys():
            return self.merge(mat=mat)


    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        n = self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"





rows = ROWS()
