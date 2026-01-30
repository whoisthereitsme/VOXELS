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



ARRAY_ARIDS = tuple[NDArray[ROW.DTYPE], dict[int,int]]



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
        self.n:dict[int, int] = {mid: 0 for mid in range(MATERIALS.NUM)}  # number of valid rows per material
        self.m = 0  # for the total number of rows used

        
        self.array: NDArray[ROW.DTYPE] = np.full((MATERIALS.NUM, ROWS.SIZE, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE)
        self.shape = self.array.shape
        self.nbytes = self.array.nbytes
        self.gbytes = self.nbytes / (1024**3)

        mat = "STONE"
        self.insert(p0=(ROW.XMIN, ROW.YMIN, ROW.ZMIN), p1=(ROW.XMAX, ROW.YMAX, ROW.ZMAX), mat=mat)  # alive and dirty by default are true so no need to specify : easier to use now!!!
        self.size = ROW.XMAX - ROW.XMIN, ROW.YMAX - ROW.YMIN, ROW.ZMAX - ROW.ZMIN

        self._merge = 16
        self.__merge = 0

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

    def requirements(self, n:int=None) -> tuple[NDArray[ROW.DTYPE], dict[int, int]]:
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
        """
        PUBLIC:
        - a. arguments: none
        - b. returns: total volume of all rows in all materials
        """
        total = 0
        for mid in range(MATERIALS.NUM):
            n = self.n[mid]
            for rid in range(n):
                row = self.array[mid][rid]
                total += ROW.VOLUME(row=row)
        return total

    def search(self, pos:POS=None) -> tuple[str, int, NDArray[ROW.DTYPE]]:
        """
        PRIVATE:
        - a. arguments:
           - a.1: pos: position to search for
        - b. returns: 
            - b.1: material name
            - b.2: row id within material
            - b.3: the row array at the given position
        """
        mat, rid, row = self.bvh.search(pos=pos)
        return (mat, rid, row)
    
    def get(self, mat:str=None, rid:int=None) -> NDArray[ROW.DTYPE]:
        return self.array[Materials.name2idx[mat]][rid]

    def nrows(self, mat:str=None) -> int:
        return self.n[Materials.name2idx[mat]]

    def splitrow(self, pos:POS=None, p2:POS=None, mat:str=None) -> ARRAY_ARIDS:
        mat0, rid, row = self.search(pos=pos)
        r0 = ROW.P0(row=row)
        r1 = ROW.P1(row=row)

        x0, y0, z0 = r0
        x3, y3, z3 = r1
        x1, y1, z1 = pos
        x2, y2, z2 = p2

        # (defensive) clamp to row bounds
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
    



    def split1(self, pos: POS = None, mat: str = None) -> ARRAY_ARIDS:
        p2 = (pos[0] + 1, pos[1] + 1, pos[2] + 1)
        batch, arids = self.splitrow(pos=pos, p2=p2, mat=mat)
        batch, arids = self.merge(rows=batch)
        return batch, arids
    
    def split2(self, p0: POS = None, p1: POS = None, mat: str = None) -> ARRAY_ARIDS:
        def intersect(a0, a1, b0, b1):
            q0 = (max(a0[0], b0[0]), max(a0[1], b0[1]), max(a0[2], b0[2]))
            q1 = (min(a1[0], b1[0]), min(a1[1], b1[1]), min(a1[2], b1[2]))
            if q0[0] >= q1[0] or q0[1] >= q1[1] or q0[2] >= q1[2]:
                return None
            return q0, q1
        
        if p0 is None or p1 is None or mat is None:
            raise ValueError("p0, p1, mat must be provided")

        p0, p1 = ROW.SORT(p0=p0, p1=p1)
        if p0[0] >= p1[0] or p0[1] >= p1[1] or p0[2] >= p1[2]:
            return  # empty box

        # Find the row containing the start point
        mat0, rid, row = self.search(pos=p0)
        r0 = ROW.P0(row=row)
        r1 = ROW.P1(row=row)

        hit = intersect(p0, p1, r0, r1)
        if hit is None:
            return  # shouldn't happen if partition invariant holds

        q0, q1 = hit  # portion of the requested box that lies inside THIS row

        # Carve q0..q1 in this row (generalized split1; implement as helper)
        batch, _ = self.splitrow(pos=q0, p2=q1, mat=mat)
        self.merge(rows=batch)

        # Now recurse on the leftovers by splitting along boundaries that stopped q1.
        # If q1.x < p1.x, then there is remaining region on the "right" side in X.
        # Similar for Y and Z. We recurse on up to 3 remainder boxes.

        if q1[0] < p1[0]:
            # right remainder: [ (q1.x, p0.y, p0.z) , p1 )
            self.split2(p0=(q1[0], p0[1], p0[2]), p1=p1, mat=mat)

        if q1[1] < p1[1]:
            # top remainder in Y within the already-consumed X-range
            self.split2(p0=(p0[0], q1[1], p0[2]), p1=(q1[0], p1[1], p1[2]), mat=mat)

        if q1[2] < p1[2]:
            # front remainder in Z within already-consumed X,Y range
            self.split2(p0=(p0[0], p0[1], q1[2]), p1=(q1[0], q1[1], p1[2]), mat=mat)

    
    def split(self, pos:POS=None, pos1:POS=None, mat:str=None) -> ARRAY_ARIDS:
        """
        PUBLIC:
        - a. arguments:
            - a.1: pos: position to split at (single point split)
            - a.2: pos1: opposite corner position to split to (box split) (optional)
            - a.3: mat: material to assign to the new split rows
        - b. returns:
            - b.1: batch: array of newly created rows
        """
        if mat is None:
            raise ValueError("material must be specified")
        if pos is None and pos1 is None:
            raise ValueError("either pos or pos1 must be provided")
        if pos1 is not None and pos is not None:
            array = self.split2(p0=pos, p1=pos1, mat=mat)
        if pos1 is None and pos is not None:
            array = self.split1(pos=pos, mat=mat)
        if pos is None and pos1 is not None:
            array = self.split1(pos=pos1, mat=mat)
         
        return self.merge(rows=array)


    def merge2(self, mat:str=None, rid0:int=None, rid1:int=None) -> ARRAY_ARIDS:
        mid = Materials.name2idx[mat]
        n = self.n[mid]
        if rid0 < 0 or rid0 >= n or rid1 < 0 or rid1 >= n or rid0 == rid1:
            return False

        row0 = self.array[mid][rid0]
        row1 = self.array[mid][rid1]

        touch = ROW.MERGE(row0=row0, row1=row1)
        if touch == (False, False, False):
            return False

        p0 = ROW.SORT(p0=ROW.P0(row=row0), p1=ROW.P0(row=row1))[0]
        p1 = ROW.SORT(p0=ROW.P1(row=row0), p1=ROW.P1(row=row1))[1]

        hi = rid0 if rid0 > rid1 else rid1
        lo = rid1 if hi == rid0 else rid0
        self.remove(mat=mat, index=hi)
        self.remove(mat=mat, index=lo)
        self.insert(p0=p0, p1=p1, mat=mat)
        return True

    def mergeax(self, mat:str=None, axis:int=None) -> ARRAY_ARIDS:
        mid = Materials.name2idx[mat]
        merges = 0
        extra: list[int] = list(range(self.n[mid] - 1, -1, -1))
        seen: set[int] = set()

        while extra:
            rid = extra.pop()

            if rid < 0 or rid >= self.n[mid]:
                continue

            if rid in seen:
                continue
            seen.add(rid)

            partner = self.mdx.search(mid=mid, rid=rid, axis=axis)
            if partner is None:
                continue

            pmid, prid = partner
            if pmid != mid or prid < 0 or prid >= self.n[mid]:
                continue

            if self.merge2(mat=mat, rid0=rid, rid1=prid):
                merges += 1
                new_rid = self.n[mid] - 1
                extra.append(new_rid)

                if hasattr(self.mdx, "neighbors_of"):
                    neigh = self.mdx.neighbors_of(mid=mid, rid=new_rid)
                    for nm, nr in neigh:
                        if nm != mid:
                            continue

                        if nr in seen:
                            seen.remove(nr)
                        extra.append(nr)

                if rid < self.n[mid]:
                    if rid in seen:
                        seen.remove(rid)
                    extra.append(rid)

        return merges
        
    def mergemat(self, mat:str=None) -> ARRAY_ARIDS:
        for ax in range(3):
            merged = self.mergeax(mat=mat, axis=ax) > 0
            while merged == True:
                merged = self.mergeax(mat=mat, axis=ax) > 0
             
    def mergerows(self, rows:NDArray[ROW.DTYPE]=None) -> int:
        if rows is None:
            return 0

        mids_present: set[int] = set()
        for mid in range(rows.shape[0]):
            for i in range(rows.shape[1]):
                if rows[mid][i][*ROW.IDS_ID] != ROW.SENTINEL:
                    mids_present.add(mid)
                    break

        total_merges = 0

        while True:
            merged_this_round = 0

            for ax in (self.mdx.AX_X, self.mdx.AX_Y, self.mdx.AX_Z):
                extra: list[tuple[int, int]] = []
                for mid in mids_present:
                    for rid in range(self.n[mid] - 1, -1, -1):
                        extra.append((mid, rid))

                seen: set[tuple[int, int]] = set()

                while extra:
                    mid, rid = extra.pop()
                    if rid < 0 or rid >= self.n[mid]:
                        continue

                    key = (mid, rid)
                    if key in seen:
                        continue
                    seen.add(key)

                    partner = self.mdx.search(mid=mid, rid=rid, axis=ax)
                    if partner is None:
                        continue

                    pmid, prid = partner
                    if pmid != mid or prid < 0 or prid >= self.n[mid]:
                        continue

                    mat = self.mats.idx2name[mid]

                    if self.merge2(mat=mat, rid0=rid, rid1=prid):
                        merged_this_round += 1
                        total_merges += 1

                        new_rid = self.n[mid] - 1
                        extra.append((mid, new_rid))

                        # recheck the slot that got swapped-in
                        if rid < self.n[mid]:
                            seen.discard((mid, rid))
                            extra.append((mid, rid))

            if merged_this_round == 0:
                break

        return total_merges

    
    def mergeall(self) -> ARRAY_ARIDS:
        for mat in self.mats.name2idx.keys():
            self.mergemat(mat=mat)
        
    def merge(self, rows:NDArray[ROW.DTYPE]=None) -> ARRAY_ARIDS:
        """
        PUBLIC:
        - a. arguments:
            - a.1: rows: array of rows to consider for merging; if None, all rows are considered
        - b. returns: None
        """
        if rows is None:
            self.mergeall()
        if rows is not None:
            self.mergerows(rows=rows)


    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        n = self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"



# INSTRUCTIONS:
# make merge() and all its derivates return -> a array ( array: NDArray[ROW.DTYPE] = np.full((MATERIALS.NUM, nrowsgenerated, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE) )
# make split() and all its derivates return -> a array ( array: NDArray[ROW.DTYPE] = np.full((MATERIALS.NUM, nrowsgenerated, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE) )

# call merge(rows=rows) after split1 operations to consolidate newly created rows ( the merged ones are returned by split() )
# call merge(rows=rows) after split2 operations to consolidate newly created rows ( the merged ones are returned by split() )
# the merge in split2 ensures not all rows that are result of split2 are accumulated but only the merged ones are accumulated

# this ensures the split2 also keeps the nrows at any point as low as possible!!!
# in the end of split2 we merge(rows=rows) again for all the merged ones that where result of the split2 operations befroe

# this ensures at any point the nrows is kept as low as possible!!! and makes everything compatible with eachother 

# ps keep a arids dict next to the batch array in splitrow to track how many rows where created per material in that batch
# so that we can keep trak of how many rows where created per material in that split or merge operation

# allready changed the signatures of split() and merge() and all their derivates to return the array of created rows
# now need to propagate that through all the calls and ensure the calls to split() and merge() are updated accordingly

# keep the remove and insert as they are no need to change them becouse they ensure the internal state is always correct

# also added a requirements(n:int) -> tuple[NDArray[ROW.DTYPE], dict[int, int]] helper to create the batch array and arids dict together
# and added a shortname for tuple[NDArray[ROW.DTYPE], dict[int, int]] as ARRAY_ARIDS for better readability

# so no need to change anything else just propagate the new return types and ensure the calls are updated accordingly
# respond with the full code so leave not even a single function or method out of it
# do not add methods that are not there already its not required at all

# formatting rules:
# use arg:argtype=None for all arguments (eg. def func(arg1:argtype1=None, arg2:argtype2=None) -> returntype: )
# use a space between arg1:argtype1=None and arg2:argtype2=None (eg. def func(arg1:argtype1=None, arg2:argtype2=None) -> returntype: )
# wrong: def func(arg1:argtype1=None,arg2:argtype2=None)->returntype:
# wrong : def func( arg1 : argtype1 = None , arg2 : argtype2 = None ) -> returntype :
# right: def func(arg1:argtype1=None, arg2:argtype2=None) -> returntype:

# if you have more questions or assumtions do not respond with full code yet but ask first
# if you have no questions anymore respond with the full code only
# use methods that are avaible as much as possible!!! to avoid redoing work that is already done!!!
# do not change the logic of any method unless required for the new return types!!!

# use also the methods in ROW as much as possible to avoid redoing work that is already done there!!!