from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from world._rows import ROWS
    from utils.types import POS

from world.row import ROW





class BVH:
    __slots__ = (
        "rows",
        "root",
        "left",
        "right",
        "parent",
        # AABB as 6 parallel lists (SoA)
        "xmin",
        "ymin",
        "zmin",
        "xmax",
        "ymax",
        "zmax",
        # leaf as 2 parallel lists
        "leaf_mid",
        "leaf_rid",
        # fast delete index
        "leaf_index",
    )

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

        self.leaf_mid: list[int] = []
        self.leaf_rid: list[int] = []

        # (mid, rid) -> node index
        self.leaf_index: dict[tuple[int, int], int] = {}

    # ------------------------------------------------------------------
    # node alloc
    # ------------------------------------------------------------------

    def _new_node(
        self,
        xmin: int,
        ymin: int,
        zmin: int,
        xmax: int,
        ymax: int,
        zmax: int,
        leaf_mid: int = -1,
        leaf_rid: int = -1,
        left: int = -1,
        right: int = -1,
        parent: int = -1,
    ) -> int:
        i = len(self.left)

        self.left.append(left)
        self.right.append(right)
        self.parent.append(parent)

        self.xmin.append(xmin)
        self.ymin.append(ymin)
        self.zmin.append(zmin)
        self.xmax.append(xmax)
        self.ymax.append(ymax)
        self.zmax.append(zmax)

        self.leaf_mid.append(leaf_mid)
        self.leaf_rid.append(leaf_rid)
        return i

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _volume(xmin: int, ymin: int, zmin: int, xmax: int, ymax: int, zmax: int) -> int:
        return (xmax - xmin) * (ymax - ymin) * (zmax - zmin)

    def _merged_volume_with_node(
        self,
        node: int,
        bxmin: int,
        bymin: int,
        bzmin: int,
        bxmax: int,
        bymax: int,
        bzmax: int,
    ) -> int:
        axmin = self.xmin[node]
        aymin = self.ymin[node]
        azmin = self.zmin[node]
        axmax = self.xmax[node]
        aymax = self.ymax[node]
        azmax = self.zmax[node]

        mxmin = axmin if axmin < bxmin else bxmin
        mymin = aymin if aymin < bymin else bymin
        mzmin = azmin if azmin < bzmin else bzmin
        mxmax = axmax if axmax > bxmax else bxmax
        mymax = aymax if aymax > bymax else bymax
        mzmax = azmax if azmax > bzmax else bzmax

        return self._volume(mxmin, mymin, mzmin, mxmax, mymax, mzmax)

    def _fix_upwards(self, node:int=None) -> None:
        while node != -1:
            l = self.left[node]
            r = self.right[node]

            self.xmin[node] = self.xmin[l] if self.xmin[l] < self.xmin[r] else self.xmin[r]
            self.ymin[node] = self.ymin[l] if self.ymin[l] < self.ymin[r] else self.ymin[r]
            self.zmin[node] = self.zmin[l] if self.zmin[l] < self.zmin[r] else self.zmin[r]
            self.xmax[node] = self.xmax[l] if self.xmax[l] > self.xmax[r] else self.xmax[r]
            self.ymax[node] = self.ymax[l] if self.ymax[l] > self.ymax[r] else self.ymax[r]
            self.zmax[node] = self.zmax[l] if self.zmax[l] > self.zmax[r] else self.zmax[r]

            node = self.parent[node]

    # ------------------------------------------------------------------
    # insertion
    # ------------------------------------------------------------------

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
            xmin, ymin, zmin,
            xmax, ymax, zmax,
            leaf_mid=mid,
            leaf_rid=rid,
        )

        self.leaf_index[(mid, rid)] = leaf_node

        if self.root == -1:
            self.root = leaf_node
            return

        self.root = self._insert_node(self.root, leaf_node)

    def _insert_node(self, root: int, leaf_node: int) -> int:
        bxmin = self.xmin[leaf_node]; bymin = self.ymin[leaf_node]; bzmin = self.zmin[leaf_node]
        bxmax = self.xmax[leaf_node]; bymax = self.ymax[leaf_node]; bzmax = self.zmax[leaf_node]

        node = root
        while self.leaf_mid[node] == -1:
            l = self.left[node]
            r = self.right[node]
            node = (
                l if self._merged_volume_with_node(l, bxmin, bymin, bzmin, bxmax, bymax, bzmax)
                < self._merged_volume_with_node(r, bxmin, bymin, bzmin, bxmax, bymax, bzmax)
                else r
            )

        old_leaf = node
        parent = self.parent[old_leaf]

        axmin = self.xmin[old_leaf]; aymin = self.ymin[old_leaf]; azmin = self.zmin[old_leaf]
        axmax = self.xmax[old_leaf]; aymax = self.ymax[old_leaf]; azmax = self.zmax[old_leaf]

        new_parent = self._new_node(
            axmin if axmin < bxmin else bxmin,
            aymin if aymin < bymin else bymin,
            azmin if azmin < bzmin else bzmin,
            axmax if axmax > bxmax else bxmax,
            aymax if aymax > bymax else bymax,
            azmax if azmax > bzmax else bzmax,
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
        self._fix_upwards(parent)
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
            found = self.leaf_index.pop((mid, rid))
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
            self._fix_upwards(grand)

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(self, pos:POS=None) -> tuple[str, int, "NDArray[ROW.DTYPE]"]:
        if self.root == -1:
            raise LookupError("[ERROR] BVH.search() failed: empty BVH")

        x, y, z = pos
        stack = [self.root]

        xminL = self.xmin; yminL = self.ymin; zminL = self.zmin
        xmaxL = self.xmax; ymaxL = self.ymax; zmaxL = self.zmax
        leftL = self.left; rightL = self.right
        leaf_midL = self.leaf_mid; leaf_ridL = self.leaf_rid
        rows_arr = self.rows.array
        idx2name = self.rows.mats.idx2name

        while stack:
            n = stack.pop()
            if n == -1:
                continue

            if not (xminL[n] <= x < xmaxL[n] and yminL[n] <= y < ymaxL[n] and zminL[n] <= z < zmaxL[n]):
                continue

            mid = leaf_midL[n]
            if mid != -1:
                rid = leaf_ridL[n]
                row = rows_arr[mid][rid]
                if ROW.CONTAINS(row=row, pos=pos):
                    return idx2name[mid], rid, row
                continue

            l = leftL[n]
            r = rightL[n]

            if l != -1 and (xminL[l] <= x < xmaxL[l] and yminL[l] <= y < ymaxL[l] and zminL[l] <= z < zmaxL[l]):
                stack.append(l)
            if r != -1 and (xminL[r] <= x < xmaxL[r] and yminL[r] <= y < ymaxL[r] and zminL[r] <= z < zmaxL[r]):
                stack.append(r)

        raise LookupError("[ERROR] BVH.search() failed: point not found (partition invariant violated or BVH not updated)")















