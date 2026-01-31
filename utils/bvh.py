from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from world.rows import ROWS
    from utils.types import POS

from world.row import ROW





class BVH:
    __slots__ = ("rows", "root", "left", "right", "parent", "x0", "y0", "z0", "x1", "y1", "z1", "lmid", "lrid", "lidx")
    def __init__(self, rows:ROWS=None) -> None:
        self.rows: ROWS = rows
        self.root: int = -1
        self.x0, self.y0, self.z0, self.x1, self.y1, self.z1, self.lmid, self.lrid, self.left, self.right, self.parent = [], [], [], [], [], [], [], [], [], [], []
        self.lidx: dict[tuple[int, int], int] = {}

    def newnode(self, x0:int=None, y0:int=None, z0:int=None, x1:int=None, y1:int=None, z1:int=None, lmid:int=-1, lrid:int=-1, left:int=-1, right:int=-1, parent:int=-1) -> int:
        i = len(self.left)

        self.left.append(left)
        self.right.append(right)
        self.parent.append(parent)

        self.x0.append(x0)
        self.y0.append(y0)
        self.z0.append(z0)
        self.x1.append(x1)
        self.y1.append(y1)
        self.z1.append(z1)

        self.lmid.append(lmid)
        self.lrid.append(lrid)
        return i


    def volume(self, x0:int=None, y0:int=None, z0:int=None, x1:int=None, y1:int=None, z1:int=None) -> int:
        return (x1 - x0) * (y1 - y0) * (z1 - z0)

    def mergedvolume(self, node:int=None, bx0:int=None, by0:int=None, bz0:int=None, bx1:int=None, by1:int=None, bz1:int=None) -> int:
        ax0, ay0, az0 = self.x0[node], self.y0[node], self.z0[node]
        ax1, ay1, az1 = self.x1[node], self.y1[node], self.z1[node]

        x0, y0, z0 = min(ax0, bx0), min(ay0, by0), min(az0, bz0)
        x1, y1, z1 = max(ax1, bx1), max(ay1, by1), max(az1, bz1)
        return self.volume(x0=x0, y0=y0, z0=z0, x1=x1, y1=y1, z1=z1)

    def fixupwards(self, node:int=None) -> None:
        while node != -1:
            l, r = self.left[node], self.right[node]

            self.x0[node], self.y0[node], self.z0[node] = min(self.x0[l], self.x0[r]), min(self.y0[l], self.y0[r]), min(self.z0[l], self.z0[r])
            self.x1[node], self.y1[node], self.z1[node] = max(self.x1[l], self.x1[r]), max(self.y1[l], self.y1[r]), max(self.z1[l], self.z1[r])
            node = self.parent[node]


    def insert(self, mat:str=None, rid:int=None, row:NDArray[ROW.DTYPE]=None, fixup:bool=False) -> None:
        if row is None:
            mid = self.rows.mats.name2idx[mat]
            row = self.rows.array[mid][rid]
        else:
            mat_id = int(row[*ROW.IDS_MAT])
            mid = self.rows.mats.id2idx[mat_id]
            rid = int(row[*ROW.IDS_ID])

        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)

        leaf_node = self.newnode(x0=x0, y0=y0, z0=z0, x1=x1, y1=y1, z1=z1, lmid=mid, lrid=rid)
        self.lidx[(mid, rid)] = leaf_node

        if self.root == -1:
            self.root = leaf_node
            return

        self.root = self.insertnode(leaf=leaf_node, fixup=fixup)

    def insertnode(self, leaf:int=None, fixup:bool=False) -> int:
        bx0, by0, bz0 = self.x0[leaf], self.y0[leaf], self.z0[leaf]
        bx1, by1, bz1 = self.x1[leaf], self.y1[leaf], self.z1[leaf]
        root = node = self.root
        while self.lmid[node] == -1:
            l, r = self.left[node], self.right[node]
            v0 = self.mergedvolume(node=l, bx0=bx0, by0=by0, bz0=bz0, bx1=bx1, by1=by1, bz1=bz1)
            v1 = self.mergedvolume(node=r, bx0=bx0, by0=by0, bz0=bz0, bx1=bx1, by1=by1, bz1=bz1)
            node = (l if v0 < v1 else r)

        leaf0 = node
        parent0 = self.parent[leaf0]

        ax0, ay0, az0 = self.x0[leaf0], self.y0[leaf0], self.z0[leaf0]
        ax1, ay1, az1 = self.x1[leaf0], self.y1[leaf0], self.z1[leaf0]
        parent1 = self.newnode(x0=min(ax0, bx0), y0=min(ay0, by0), z0=min(az0, bz0), x1=max(ax1, bx1), y1=max(ay1, by1), z1=max(az1, bz1))

        self.left[parent1], self.right[parent1] = leaf0, leaf
        self.parent[leaf0] = self.parent[leaf] = parent1

        if parent0 == -1:
            return parent1

        if self.left[parent0] == leaf0:
            self.left[parent0] = parent1
        else:
            self.right[parent0] = parent1

        self.parent[parent1] = parent0
        if fixup:
            self.fixupwards(node=parent0)
        return root

    def remove(self, mat:str=None, rid:int=None, row:NDArray[ROW.DTYPE]=None) -> None:
        if row is not None:
            mid, rid = self.rows.mats.id2idx[row[*ROW.IDS_MAT]], row[*ROW.IDS_ID]
        else:
            mid = self.rows.mats.name2idx[mat]

        try:
            found = self.lidx.pop((mid, rid))
        except KeyError:
            raise KeyError("[ERROR] BVH.remove() failed: row not found in BVH")

        parent = self.parent[found]
        if parent == -1:
            self.root = -1
            return

        sibling = self.right[parent] if self.left[parent] == found else self.left[parent]
        grand = self.parent[parent]

        if grand == -1:
            self.root = sibling
            self.parent[sibling] = -1
        else:
            if self.left[grand] == parent:
                self.left[grand] = sibling
            else:
                self.right[grand] = sibling
            self.parent[sibling] = grand
            self.fixupwards(grand)

    def search(self, pos:POS=None) -> tuple[str, int, "NDArray[ROW.DTYPE]"]:
        if self.root == -1:
            raise LookupError("[ERROR] BVH.search() failed: empty BVH")

        x, y, z = pos
        stack = [self.root]

        x0, y0, z0, x1, y1, z1 = self.x0, self.y0, self.z0, self.x1, self.y1, self.z1
        l0, r0, lm, lr = self.left, self.right, self.lmid, self.lrid

        while stack:
            n = stack.pop()
            if n == -1:
                continue

            if not (x0[n] <= x < x1[n] and y0[n] <= y < y1[n] and z0[n] <= z < z1[n]):
                continue

            mid = lm[n]
            if mid != -1:
                row = self.rows.array[mid][lr[n]]
                if ROW.CONTAINS(row=row, pos=pos):
                    mid = self.rows.mats.idx2name[mid]
                    return mid, lr[n], row
                continue

            l, r = l0[n], r0[n]
            if l != -1 and (x0[l] <= x < x1[l] and y0[l] <= y < y1[l] and z0[l] <= z < z1[l]):
                stack.append(l)
            if r != -1 and (x0[r] <= x < x1[r] and y0[r] <= y < y1[r] and z0[r] <= z < z1[r]):
                stack.append(r)

        raise LookupError("[ERROR] BVH.search() failed: point not found (partition invariant violated or BVH not updated)")















