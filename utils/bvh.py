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
        self.rows = rows
        self.root: int = -1

        self.left: list[int] = []
        self.right: list[int] = []
        self.parent: list[int] = []

        self.x0 = self.y0 = self.z0 = []
        self.x1 = self.y1 = self.z1 = []

        self.lmid: list[int] = []
        self.lrid: list[int] = []
        self.lidx: dict[tuple[int, int], int] = {}

    def _new_node(self, x0:int=None, y0:int=None, z0:int=None, x1:int=None, y1:int=None, z1:int=None, lmid:int=-1, lrid:int=-1, left:int=-1, right:int=-1, parent:int=-1) -> int:
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

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def volume(xmin:int=None, ymin:int=None, zmin:int=None, xmax:int=None, ymax:int=None, zmax:int=None) -> int:
        return (xmax - xmin) * (ymax - ymin) * (zmax - zmin)

    def _merged_volume_with_node(self, node:int=None, bxmin:int=None, bymin:int=None, bzmin:int=None, bxmax:int=None, bymax:int=None, bzmax:int=None) -> int:
        ax0, ay0, az0 = self.x0[node], self.y0[node], self.z0[node]
        ax1, ay1, az1 = self.x1[node], self.y1[node], self.z1[node]

        x0, x1 = min(ax0, bxmin), max(ax1, bxmax)
        y0, y1 = min(ay0, bymin), max(ay1, bymax)
        z0, z1 = min(az0, bzmin), max(az1, bzmax)

        return self.volume(xmin=x0, ymin=y0, zmin=z0, xmax=x1, ymax=y1, zmax=z1)

    def fixupwards(self, node:int=None) -> None:
        while node != -1:
            l, r = self.left[node], self.right[node]

            self.x0[node] = min(self.x0[l], self.x0[r])
            self.y0[node] = min(self.y0[l], self.y0[r])
            self.z0[node] = min(self.z0[l], self.z0[r])
            self.z1[node] = max(self.z1[l], self.z1[r])
            self.y1[node] = max(self.y1[l], self.y1[r])
            self.z1[node] = max(self.z1[l], self.z1[r])

            node = self.parent[node]


    def insert(self, mat:str=None, rid:int=None, row:NDArray[ROW.DTYPE]=None) -> None:
        if row is None:
            mid = self.rows.mats.name2idx[mat]
            row = self.rows.array[mid][rid]
        else:
            mat_id = int(row[*ROW.IDS_MAT])
            mid = self.rows.mats.id2idx[mat_id]
            rid = int(row[*ROW.IDS_ID])

        xmin, ymin, zmin = ROW.P0(row)
        xmax, ymax, zmax = ROW.P1(row)

        leaf_node = self._new_node(
            x0=xmin, y0=ymin, z0=zmin,
            x1=xmax, y1=ymax, z1=zmax,
            lmid=mid,
            lrid=rid,
        )

        self.lidx[(mid, rid)] = leaf_node

        if self.root == -1:
            self.root = leaf_node
            return

        self.root = self._insert_node(self.root, leaf_node)

    def _insert_node(self, root: int, leaf_node: int) -> int:
        bxmin, bxmax = self.x0[leaf_node], self.x1[leaf_node]
        bymin, bymax = self.y0[leaf_node], self.y1[leaf_node]
        bzmin, bzmax = self.z0[leaf_node], self.z1[leaf_node]

        node = root
        while self.lmid[node] == -1:
            l = self.left[node]
            r = self.right[node]
            node = (
                l if self._merged_volume_with_node(node=l, bxmin=bxmin, bymin=bymin, bzmin=bzmin, bxmax=bxmax, bymax=bymax, bzmax=bzmax)
                < self._merged_volume_with_node(node=r, bxmin=bxmin, bymin=bymin, bzmin=bzmin, bxmax=bxmax, bymax=bymax, bzmax=bzmax)
                else r
            )

        old_leaf = node
        parent = self.parent[old_leaf]

        ax0, ay0, az0 = self.x0[old_leaf], self.y0[old_leaf], self.z0[old_leaf]
        ax1, ay1, az1 = self.x1[old_leaf], self.y1[old_leaf], self.z1[old_leaf]

        new_parent = self._new_node(
            min(ax0, bxmin),
            min(ay0, bymin),
            min(az0, bzmin),
            max(ax1, bxmax),
            max(ay1, bymax),
            max(az1, bzmax),
        )

        self.left[new_parent] = old_leaf
        self.right[new_parent] = leaf_node
        self.parent[old_leaf] = new_parent
        self.parent[leaf_node] = new_parent

        if parent == -1:
            return new_parent

        if self.left[parent] == old_leaf:
            self.left[parent] = new_parent
        else:
            self.right[parent] = new_parent

        self.parent[new_parent] = parent
        self.fixupwards(parent)
        return root

    # ------------------------------------------------------------------
    # removal (FAST)
    # ------------------------------------------------------------------

    def remove(self, mat:str=None, rid:int=None, row:NDArray[ROW.DTYPE]=None) -> None:
        if row is not None:
            mat_id = int(row[*ROW.IDS_MAT])
            mid = self.rows.mats.id2idx[mat_id]
            rid = int(row[*ROW.IDS_ID])
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

        x0, y0, z0 = self.x0, self.y0, self.z0
        x1, y1, z1 = self.x1, self.y1, self.z1
        l0, r0 = self.left, self.right
        lm, lr = self.lmid, self.lrid

        while stack:
            n = stack.pop()
            if n == -1:
                continue

            if not (x0[n] <= x < x1[n] and y0[n] <= y < y1[n] and z0[n] <= z < z1[n]):
                continue

            mid = lm[n]
            if mid != -1:
                rid = lr[n]
                row = self.rows.array[mid][rid]
                if ROW.CONTAINS(row=row, pos=pos):
                    mid = self.rows.mats.idx2name[mid]
                    return mid, rid, row
                continue

            l, r = l0[n], r0[n]
            if l != -1 and (x0[l] <= x < x1[l] and y0[l] <= y < y1[l] and z0[l] <= z < z1[l]):
                stack.append(l)
            if r != -1 and (x0[r] <= x < x1[r] and y0[r] <= y < y1[r] and z0[r] <= z < z1[r]):
                stack.append(r)

        raise LookupError("[ERROR] BVH.search() failed: point not found (partition invariant violated or BVH not updated)")















