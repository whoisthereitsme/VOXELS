# utils/bvh.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from world.rows import ROWS

from world.row import ROW
from utils.types import POS, Row


class BVH:
    __slots__ = (
        "rows",
        "root",
        "x0","y0","z0","x1","y1","z1",
        "left","right","parent",
        "lmid","lrid",
        "lidx"
    )

    def __init__(self, rows: "ROWS" = None) -> None:
        self.rows = rows
        self.root = -1

        self.x0 = []
        self.y0 = []
        self.z0 = []
        self.x1 = []
        self.y1 = []
        self.z1 = []

        self.left = []
        self.right = []
        self.parent = []

        self.lmid = []
        self.lrid = []

        self.lidx: dict[tuple[int,int],int] = {}

    # ============================================================
    # node helpers
    # ============================================================

    def newnode(
        self,
        x0:int,y0:int,z0:int,
        x1:int,y1:int,z1:int,
        lmid:int=-1,lrid:int=-1,
        left:int=-1,right:int=-1,parent:int=-1
    )->int:
        idx = len(self.x0)

        self.x0.append(x0)
        self.y0.append(y0)
        self.z0.append(z0)
        self.x1.append(x1)
        self.y1.append(y1)
        self.z1.append(z1)

        self.left.append(left)
        self.right.append(right)
        self.parent.append(parent)

        self.lmid.append(lmid)
        self.lrid.append(lrid)

        return idx

    def expand(self, a:int, b:int)->None:
        self.x0[a] = min(self.x0[a], self.x0[b])
        self.y0[a] = min(self.y0[a], self.y0[b])
        self.z0[a] = min(self.z0[a], self.z0[b])
        self.x1[a] = max(self.x1[a], self.x1[b])
        self.y1[a] = max(self.y1[a], self.y1[b])
        self.z1[a] = max(self.z1[a], self.z1[b])

    def area(self, n:int)->int:
        return (
            (self.x1[n]-self.x0[n]) *
            (self.y1[n]-self.y0[n]) *
            (self.z1[n]-self.z0[n])
        )

    def insert(self, row:Row=None)->None:
        mid,rid,row = int(row.mid),int(row.rid),row.row
        x0,y0,z0 = ROW.P0(row=row)
        x1,y1,z1 = ROW.P1(row=row)

        leaf = self.newnode(
            x0,y0,z0,x1,y1,z1,
            lmid=mid,lrid=rid
        )
        self.lidx[(mid,rid)] = leaf

        if self.root == -1:
            self.root = leaf
            return

        self.root = self.insertnode(self.root, leaf)

    def insertnode(self, root:int, leaf:int)->int:
        if self.lmid[root] != -1:
            parent = self.newnode(
                min(self.x0[root], self.x0[leaf]),
                min(self.y0[root], self.y0[leaf]),
                min(self.z0[root], self.z0[leaf]),
                max(self.x1[root], self.x1[leaf]),
                max(self.y1[root], self.y1[leaf]),
                max(self.z1[root], self.z1[leaf]),
                left=root,
                right=leaf
            )
            self.parent[root] = parent
            self.parent[leaf] = parent
            return parent

        l = self.left[root]
        r = self.right[root]

        cost_l = self.area(self.merge_cost(l, leaf))
        cost_r = self.area(self.merge_cost(r, leaf))

        if cost_l <= cost_r:
            self.left[root] = self.insertnode(l, leaf)
            self.parent[self.left[root]] = root
        else:
            self.right[root] = self.insertnode(r, leaf)
            self.parent[self.right[root]] = root

        self.expand(root, leaf)
        return root

    def merge_cost(self, a:int, b:int)->int:
        return self.newnode(
            min(self.x0[a], self.x0[b]),
            min(self.y0[a], self.y0[b]),
            min(self.z0[a], self.z0[b]),
            max(self.x1[a], self.x1[b]),
            max(self.y1[a], self.y1[b]),
            max(self.z1[a], self.z1[b])
        )

    def fixupwards(self, n:int)->None:
        while n != -1:
            l = self.left[n]
            r = self.right[n]
            self.x0[n] = min(self.x0[l], self.x0[r])
            self.y0[n] = min(self.y0[l], self.y0[r])
            self.z0[n] = min(self.z0[l], self.z0[r])
            self.x1[n] = max(self.x1[l], self.x1[r])
            self.y1[n] = max(self.y1[l], self.y1[r])
            self.z1[n] = max(self.z1[l], self.z1[r])
            n = self.parent[n]

    # ============================================================
    # removal
    # ============================================================

    def remove(self, row:Row=None)->None:
        mid,rid = int(row.mid),int(row.rid)
        node = self.lidx.pop((mid,rid),None)
        if node is None:
            return

        parent = self.parent[node]
        if parent == -1:
            self.root = -1
            return

        sibling = (
            self.right[parent]
            if self.left[parent] == node
            else self.left[parent]
        )
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

    def search(self, pos:POS)->Row:
        if self.root == -1:
            raise LookupError("BVH empty")

        x,y,z = pos
        stack = [self.root]

        while stack:
            n = stack.pop()
            if n == -1:
                continue

            if not (
                self.x0[n] <= x < self.x1[n] and
                self.y0[n] <= y < self.y1[n] and
                self.z0[n] <= z < self.z1[n]
            ):
                continue

            if self.lmid[n] != -1:
                mid = int(self.lmid[n])
                rid = int(self.lrid[n])
                row = self.rows.array[mid][rid]
                if ROW.CONTAINS(row=row,pos=pos):
                    return Row(mid=mid,rid=rid,row=row)
                continue

            stack.append(self.left[n])
            stack.append(self.right[n])

        raise LookupError("point not found")
