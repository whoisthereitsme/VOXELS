from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


import numpy as np
from numpy.typing import NDArray

from world.row import ROW
from utils.bvh import BVH
from utils.mdx import MDX
from world.materials import Materials, MATERIALS
from utils.types import POS, SIZE



ARRAY_ARIDS = tuple[NDArray[ROW.DTYPE], dict[int, int]]


class ROWS:
    """
    PUBLIC:
    - self.split(pos:POS, mat:str)
    - self.merge(rows:NDArray[ROW.DTYPE]=None)
    - self.volume()
    - self.get(mat:str, rid:int)

    PRIVATE:
    - self.newn(mat:str)
    - self.deln(mat:str)
    - self.insert(p0:POS, p1:POS, mat:str, dirty:bool=True, alive:bool=True)
    - self.remove(index:int, mat:str, row:NDArray[ROW.DTYPE])
    - self.search(pos:POS)
    - self.nrows(mat:str)
    - self.merge2(mat:str, rid0:int, rid1:int)
    - self.mergeax(mat:str, axis:int)
    - self.mergemat(mat:str)
    - self.mergerows(rows:NDArray[ROW.DTYPE])
    - self.mergeall()
    """
    SIZE = 65536

    def __init__(self) -> None:
        self.mats = Materials()
        self.bvh = BVH(rows=self)
        self.mdx = MDX(rows=self)
        
        self.total = 0
        self.array, self.arids = self.requirements(ROWS.SIZE)
        self.shape = self.array.shape
        self.nbytes = self.array.nbytes
        self.gbytes = self.nbytes / (1024**3)

        self.insert(p0=(ROW.XMIN, ROW.YMIN, ROW.ZMIN), p1=(ROW.XMAX, ROW.YMAX, ROW.ZMAX), mat="STONE")
        self.size = (ROW.XMAX - ROW.XMIN, ROW.YMAX - ROW.YMIN, ROW.ZMAX - ROW.ZMIN)
        self.vol = self.volume()

    def newn(self, mat:str=None) -> int:
        mid: int = Materials.name2idx[mat]
        n: int = self.arids[mid]
        self.arids[mid] += 1
        self.total += 1
        return n


    def deln(self, mat:str=None) -> int:
        if mat is None:
            raise ValueError("material must be specified")
        mid = Materials.name2idx[mat]
        if self.arids[mid] <= 0:
            raise ValueError("no rows to free")
        self.arids[mid] -= 1
        self.total -= 1
        return self.arids[mid]


    def requirements(self, n:int=None) -> ARRAY_ARIDS:
        array = np.full((MATERIALS.NUM, n, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE)
        arids: dict[int, int] = {mid: 0 for mid in range(MATERIALS.NUM)}
        return (array, arids)

    def insert(self, p0:POS=None, p1:POS=None, mat:str=None, dirty:bool=True, alive:bool=True) -> NDArray[ROW.DTYPE]:
        mid: int = Materials.name2idx[mat]
        rid: int = self.newn(mat=mat)
        row = ROW.new(p0=p0, p1=p1, mat=mat, rid=rid, dirty=dirty, alive=alive)
        self.array[mid][rid] = row
        self.bvh.insert(row=row)
        self.mdx.insert(row=row)
        return row

    def remove(self, index:int=None, mat:str=None, row:NDArray[ROW.DTYPE]=None) -> NDArray[ROW.DTYPE]:
        if row is not None and index is None and mat is None:
            mat = ROW.MAT(row=row)
            index = ROW.RID(row=row)
        mid = Materials.name2idx[mat]
        n = self.arids[mid]
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

    def volume(self, mat:str=None) -> int:
        volume = 0
        if mat is None:
            for mid in range(MATERIALS.NUM):
                volume += self.volume(mat=Materials.idx2name[mid])   # add up all materials
        else:
            mid = Materials.name2idx[mat]
            for rid in range(self.arids[mid]):
                volume += ROW.VOLUME(row=self.array[mid][rid])
        return volume

    def search(self, pos:POS=None) -> tuple[str, int, NDArray[ROW.DTYPE]]:
        mat, rid, row = self.bvh.search(pos=pos)
        return (mat, rid, row)

    def get(self, mat:str=None, rid:int=None) -> NDArray[ROW.DTYPE]:
        return self.array[Materials.name2idx[mat]][rid]

    def nrows(self, mat:str=None) -> int:
        return self.arids[Materials.name2idx[mat]]

    def splitrow(self, pos:POS=None, p2:POS=None, mat:str=None) -> ARRAY_ARIDS:
        mat0, rid, row = self.search(pos=pos)
        r0 = ROW.P0(row=row)
        r1 = ROW.P1(row=row)

        x0, y0, z0 = r0
        x3, y3, z3 = r1
        x1, y1, z1 = pos
        x2, y2, z2 = p2

        x1 = max(x0, min(x1, x3)); x2 = max(x0, min(x2, x3))
        y1 = max(y0, min(y1, y3)); y2 = max(y0, min(y2, y3))
        z1 = max(z0, min(z1, z3)); z2 = max(z0, min(z2, z3))

        xs = ((x0, x1), (x1, x2), (x2, x3))
        ys = ((y0, y1), (y1, y2), (y2, y3))
        zs = ((z0, z1), (z1, z2), (z2, z3))

        array, arids = self.requirements(n=27)
        for i, (X0, X1) in enumerate(xs):
            for j, (Y0, Y1) in enumerate(ys):
                for k, (Z0, Z1) in enumerate(zs):
                    if (X1 - X0) <= 0 or (Y1 - Y0) <= 0 or (Z1 - Z0) <= 0:
                        continue

                    center = (i == 1 and j == 1 and k == 1)
                    use_mat = mat if center else mat0

                    newrow = self.insert(p0=(X0, Y0, Z0), p1=(X1, Y1, Z1), mat=use_mat)
                    mid_new = self.mats.id2idx[ROW.MID(row=newrow)]
                    array[mid_new][arids[mid_new]] = newrow
                    arids[mid_new] += 1

        self.remove(row=row)
        return array, arids

    def split1(self, pos:POS=None, mat:str=None) -> ARRAY_ARIDS:
        p2 = (pos[0] + 1, pos[1] + 1, pos[2] + 1)
        batch, arids = self.splitrow(pos=pos, p2=p2, mat=mat)
        batch, arids = self.merge(rows=batch)
        return batch, arids

    def split2(self, p0:POS=None, p1:POS=None, mat:str=None) -> ARRAY_ARIDS:
        def intersect(a0: POS = None, a1: POS = None, b0: POS = None, b1: POS = None) -> tuple[POS, POS] | None:
            q0 = (max(a0[0], b0[0]), max(a0[1], b0[1]), max(a0[2], b0[2]))
            q1 = (min(a1[0], b1[0]), min(a1[1], b1[1]), min(a1[2], b1[2]))
            if q0[0] >= q1[0] or q0[1] >= q1[1] or q0[2] >= q1[2]:
                return None
            return q0, q1

        if p0 is None or p1 is None or mat is None:
            raise ValueError("p0, p1, mat must be provided")

        p0, p1 = ROW.SORT(p0=p0, p1=p1)
        if p0[0] >= p1[0] or p0[1] >= p1[1] or p0[2] >= p1[2]:
            return self.requirements(n=0)

        acc: list[list[NDArray[ROW.DTYPE]]] = [[] for _ in range(MATERIALS.NUM)]

        mat0, rid, row = self.search(pos=p0)
        r0 = ROW.P0(row=row)
        r1 = ROW.P1(row=row)

        hit = intersect(a0=p0, a1=p1, b0=r0, b1=r1)
        if hit is None:
            return self.requirements(n=0)

        q0, q1 = hit

        batch, _ = self.splitrow(pos=q0, p2=q1, mat=mat)
        merged, marids = self.merge(rows=batch)
        for mid in range(MATERIALS.NUM):
            for i in range(marids[mid]):
                acc[mid].append(merged[mid][i])

        if q1[0] < p1[0]:
            b, a = self.split2(p0=(q1[0], p0[1], p0[2]), p1=p1, mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        if q1[1] < p1[1]:
            b, a = self.split2(p0=(p0[0], q1[1], p0[2]), p1=(q1[0], p1[1], p1[2]), mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        if q1[2] < p1[2]:
            b, a = self.split2(p0=(p0[0], p0[1], q1[2]), p1=(q1[0], q1[1], p1[2]), mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(a[mid]):
                    acc[mid].append(b[mid][i])

        arids: dict[int, int] = {mid: len(acc[mid]) for mid in range(MATERIALS.NUM)}
        n = max(arids.values()) if arids else 0
        array, out_arids = self.requirements(n=n)
        for mid in range(MATERIALS.NUM):
            out_arids[mid] = arids[mid]
            for i, r in enumerate(acc[mid]):
                array[mid][i] = r

        return array, out_arids

    def split(self, pos:POS=None, pos1:POS=None, mat:str=None) -> ARRAY_ARIDS:
        if mat is None:
            raise ValueError("material must be specified")
        if pos is None and pos1 is None:
            raise ValueError("either pos or pos1 must be provided")

        if pos1 is not None and pos is not None:
            return self.split2(p0=pos, p1=pos1, mat=mat)
        if pos1 is None and pos is not None:
            return self.split1(pos=pos, mat=mat)
        return self.split1(pos=pos1, mat=mat)

    def merge2(self, mat:str=None, rid0:int=None, rid1:int=None) -> ARRAY_ARIDS:
        mid = Materials.name2idx[mat]
        n = self.arids[mid]
        if rid0 < 0 or rid0 >= n or rid1 < 0 or rid1 >= n or rid0 == rid1:
            return self.requirements(n=0)

        row0 = self.array[mid][rid0]
        row1 = self.array[mid][rid1]

        touch = ROW.MERGE(row0=row0, row1=row1)
        if touch == (False, False, False):
            return self.requirements(n=0)

        p0 = ROW.SORT(p0=ROW.P0(row=row0), p1=ROW.P0(row=row1))[0]
        p1 = ROW.SORT(p0=ROW.P1(row=row0), p1=ROW.P1(row=row1))[1]

        hi = rid0 if rid0 > rid1 else rid1
        lo = rid1 if hi == rid0 else rid0
        self.remove(mat=mat, index=hi)
        self.remove(mat=mat, index=lo)
        newrow = self.insert(p0=p0, p1=p1, mat=mat)

        array, arids = self.requirements(n=1)
        array[mid][0] = newrow
        arids[mid] = 1
        return array, arids

    def mergeax(self, mat:str=None, axis:int=None) -> ARRAY_ARIDS:
        mid = Materials.name2idx[mat]
        start_n = self.arids[mid]
        array, arids = self.requirements(n=start_n)

        extra: list[int] = list(range(self.arids[mid] - 1, -1, -1))
        seen: set[int] = set()

        while extra:
            rid = extra.pop()

            if rid < 0 or rid >= self.arids[mid]:
                continue
            if rid in seen:
                continue
            seen.add(rid)

            partner = self.mdx.search(mid=mid, rid=rid, axis=axis)
            if partner is None:
                continue

            pmid, prid = partner
            if pmid != mid or prid < 0 or prid >= self.arids[mid]:
                continue

            created, carids = self.merge2(mat=mat, rid0=rid, rid1=prid)
            if carids[mid] > 0:
                array[mid][arids[mid]] = created[mid][0]
                arids[mid] += 1

                new_rid = self.arids[mid] - 1
                extra.append(new_rid)

                if hasattr(self.mdx, "neighbors_of"):
                    neigh = self.mdx.neighbors_of(mid=mid, rid=new_rid)
                    for nm, nr in neigh:
                        if nm != mid:
                            continue
                        if nr in seen:
                            seen.remove(nr)
                        extra.append(nr)

                if rid < self.arids[mid]:
                    if rid in seen:
                        seen.remove(rid)
                    extra.append(rid)

        return array, arids

    def mergemat(self, mat:str=None) -> ARRAY_ARIDS:
        mid = Materials.name2idx[mat]
        start_n = self.arids[mid]
        array, arids = self.requirements(n=start_n)

        for ax in range(3):
            while True:
                created, carids = self.mergeax(mat=mat, axis=ax)
                if carids[mid] <= 0:
                    break
                for i in range(carids[mid]):
                    array[mid][arids[mid]] = created[mid][i]
                    arids[mid] += 1

        return array, arids

    def mergerows(self, rows:NDArray[ROW.DTYPE]=None) -> ARRAY_ARIDS:
        if rows is None:
            return self.requirements(n=0)

        mids_present: set[int] = set()
        for mid in range(rows.shape[0]):
            for i in range(rows.shape[1]):
                if rows[mid][i][*ROW.IDS_ID] != ROW.SENTINEL:
                    mids_present.add(mid)
                    break

        # worst-case: you will never create more merged rows than currently exist in those mats combined
        worst = 0
        for mid in mids_present:
            worst += self.arids[mid]

        array, arids = self.requirements(n=worst)

        while True:
            merged_this_round = 0

            for ax in (self.mdx.AX_X, self.mdx.AX_Y, self.mdx.AX_Z):
                extra: list[tuple[int, int]] = []
                for mid in mids_present:
                    for rid in range(self.arids[mid] - 1, -1, -1):
                        extra.append((mid, rid))

                seen: set[tuple[int, int]] = set()

                while extra:
                    mid, rid = extra.pop()
                    if rid < 0 or rid >= self.arids[mid]:
                        continue

                    key = (mid, rid)
                    if key in seen:
                        continue
                    seen.add(key)

                    partner = self.mdx.search(mid=mid, rid=rid, axis=ax)
                    if partner is None:
                        continue

                    pmid, prid = partner
                    if pmid != mid or prid < 0 or prid >= self.arids[mid]:
                        continue

                    mat = self.mats.idx2name[mid]
                    created, carids = self.merge2(mat=mat, rid0=rid, rid1=prid)
                    if carids[mid] > 0:
                        array[mid][arids[mid]] = created[mid][0]
                        arids[mid] += 1
                        merged_this_round += 1

                        new_rid = self.arids[mid] - 1
                        extra.append((mid, new_rid))

                        if rid < self.arids[mid]:
                            seen.discard((mid, rid))
                            extra.append((mid, rid))

            if merged_this_round == 0:
                break

        return array, arids

    def mergeall(self) -> ARRAY_ARIDS:
        start_m = self.total
        array, arids = self.requirements(n=start_m)

        for mat in self.mats.name2idx.keys():
            created, carids = self.mergemat(mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(carids[mid]):
                    array[mid][arids[mid]] = created[mid][i]
                    arids[mid] += 1

        return array, arids

    def merge(self, rows:NDArray[ROW.DTYPE]=None) -> ARRAY_ARIDS:
        if rows is None:
            return self.mergeall()
        return self.mergerows(rows=rows)

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        n = self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"




