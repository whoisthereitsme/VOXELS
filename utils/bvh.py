from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from world.rows import ROWS
    from utils.types import POS

from world.row import ROW





class BVH:
    __slots__ = ("rows", "root", "left", "right", "parent", "xmin", "ymin", "zmin", "xmax", "ymax", "zmax", "lmid", "lrid", "lidx")

    def __init__(self, rows: ROWS) -> None:
        self.rows = rows
        self.root: int = -1

        self.left: list[int] = []
        self.right: list[int] = []
        self.parent: list[int] = []

        self.xmin: list[int] = []
        self.ymin: list[int] = []
        self.zmin: list[int] = []
        self.xmax: list[int] = []
        self.ymax: list[int] = []
        self.zmax: list[int] = []

        self.lmid: list[int] = []
        self.lrid: list[int] = []
        self.lidx: dict[tuple[int, int], int] = {}

    def _new_node(self, x0:int=None, y0:int=None, z0:int=None, x1:int=None, y1:int=None, z1:int=None, lmid:int=-1, lrid:int=-1, left:int=-1, right:int=-1, parent:int=-1) -> int:
        i = len(self.left)

        self.left.append(left)
        self.right.append(right)
        self.parent.append(parent)

        self.xmin.append(x0)
        self.ymin.append(y0)
        self.zmin.append(z0)
        self.xmax.append(x1)
        self.ymax.append(y1)
        self.zmax.append(z1)

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
        ax0, ay0, az0 = self.xmin[node], self.ymin[node], self.zmin[node]
        ax1, ay1, az1 = self.xmax[node], self.ymax[node], self.zmax[node]

        x0, x1 = min(ax0, bxmin), max(ax1, bxmax)
        y0, y1 = min(ay0, bymin), max(ay1, bymax)
        z0, z1 = min(az0, bzmin), max(az1, bzmax)

        return self.volume(xmin=x0, ymin=y0, zmin=z0, xmax=x1, ymax=y1, zmax=z1)

    def fixupwards(self, node:int=None) -> None:
        while node != -1:
            l, r = self.left[node], self.right[node]

            self.xmin[node] = min(self.xmin[l], self.xmin[r])
            self.ymin[node] = min(self.ymin[l], self.ymin[r])
            self.zmin[node] = min(self.zmin[l], self.zmin[r])
            self.xmax[node] = max(self.xmax[l], self.xmax[r])
            self.ymax[node] = max(self.ymax[l], self.ymax[r])
            self.zmax[node] = max(self.zmax[l], self.zmax[r])

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
        bxmin = self.xmin[leaf_node]; bymin = self.ymin[leaf_node]; bzmin = self.zmin[leaf_node]
        bxmax = self.xmax[leaf_node]; bymax = self.ymax[leaf_node]; bzmax = self.zmax[leaf_node]

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

        ax0, ay0, az0 = self.xmin[old_leaf], self.ymin[old_leaf], self.zmin[old_leaf]
        ax1, ay1, az1 = self.xmax[old_leaf], self.ymax[old_leaf], self.zmax[old_leaf]

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

        x0, y0, z0 = self.xmin, self.ymin, self.zmin
        x1, y1, z1 = self.xmax, self.ymax, self.zmax
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















