# world/rows.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import numpy as np
from world.materials import Materials, MATERIALS
from world.row import ROW
from utils.bvh import BVH
from utils.mdx import MDX
from utils.types import POS, SIZE, NDARR, REQS, Row


class ROWS:
    """
    PUBLIC:
    - insert(p0, p1, mat, dirty=True, alive=True) -> Row
    - remove(r:Row) -> None
    - search(pos) -> Row
    - get(mat, rid) -> Row
    - split(pos, pos1=None, mat=...) -> REQS
    - merge(rows=None) -> REQS
    - volume(mat=None) -> int
    """

    SIZE = 65536

    def __init__(self) -> None:
        self.mat = Materials()
        self.bvh = BVH(rows=self)
        self.mdx = MDX(rows=self)

        self.total = 0
        self.array, self.arids = self.reqs(n=ROWS.SIZE)
        self.shape = self.array.shape
        self.nbytes = self.array.nbytes
        self.gbytes = self.nbytes / (1024**3)

        self.p0 = (ROW.XMIN, ROW.YMIN, ROW.ZMIN)
        self.p1 = (ROW.XMAX, ROW.YMAX, ROW.ZMAX)

        # world baseline
        self.insert(p0=self.p0, p1=self.p1, mat="STONE")
        self.dim = self.size()
        self.vol = self.volume()

    # ============================================================
    # allocation / counters
    # ============================================================

    def reqs(self, n: int = None) -> REQS:
        array = np.full((MATERIALS.NUM, n, *ROW.SHAPE), fill_value=ROW.SENTINEL, dtype=ROW.DTYPE)
        arids: dict[int, int] = {mid: 0 for mid in range(MATERIALS.NUM)}
        return (array, arids)

    def newn(self, mat: str) -> int:
        mid = int(self.mat.mid(name=mat))
        rid = int(self.arids[mid])
        self.arids[mid] += 1
        self.total += 1
        return rid

    def deln(self, mid: int) -> int:
        if self.arids[mid] <= 0:
            raise ValueError("no rows to free")
        self.arids[mid] -= 1
        self.total -= 1
        return int(self.arids[mid])

    def nrows(self, mat: str = None, mid: int = None) -> int:
        if mid is None:
            if mat is None:
                raise ValueError("nrows requires mat or mid")
            mid = int(self.mat.mid(name=mat))
        return int(self.arids[int(mid)])

    # ============================================================
    # Row helpers
    # ============================================================

    def _rowview(self, mid: int, rid: int) -> NDARR:
        return self.array[int(mid)][int(rid)]

    def _wrap(self, mid: int, rid: int) -> Row:
        return Row(mid=int(mid), rid=int(rid), row=self._rowview(mid, rid))

    def get(self, mat: str = None, rid: int = None) -> Row:
        if mat is None or rid is None:
            raise ValueError("get requires mat and rid")
        mid = int(self.mat.mid(name=mat))
        rid = int(rid)
        return self._wrap(mid, rid)

    def set_into_slot(self, mid: int, rid: int, rowdata: NDARR) -> None:
        slot = self._rowview(mid, rid)
        slot[:] = rowdata

    def invalidate_slot(self, mid: int, rid: int) -> None:
        self._rowview(mid, rid)[:] = ROW.ARRAY

    # ============================================================
    # core ops
    # ============================================================

    def insert(self, p0: POS = None, p1: POS = None, mat: str = None, dirty: bool = True, alive: bool = True) -> Row:
        if mat is None:
            raise ValueError("insert requires mat")

        rid = self.newn(mat=mat)
        mid = int(self.mat.mid(name=mat))

        rowdata = ROW.new(p0=p0, p1=p1, mat=mat, rid=rid, dirty=dirty, alive=alive)
        self.set_into_slot(mid, rid, rowdata)

        r = self._wrap(mid, rid)
        self.bvh.insert(r)
        self.mdx.insert(r)
        return r

    def remove(self, r: Row) -> None:
        if r is None:
            raise ValueError("remove requires Row")

        mid = int(r.mid)
        rid = int(r.rid)

        n = self.nrows(mid=mid)
        last = n - 1

        # 1) remove target from indices
        self.bvh.remove(r)
        self.mdx.remove(r)

        # 2) if not last, move last into rid
        if rid != last:
            moved = self._wrap(mid, last)

            # remove moved entry using its ORIGINAL identity
            self.bvh.remove(moved)
            self.mdx.remove(moved)

            # copy bytes of last into rid
            moved_data = moved.row.copy()  # important: copy buffer
            moved_data[*ROW.IDS_RID] = np.uint64(rid)

            self.set_into_slot(mid, rid, moved_data)

            # reinsert with NEW identity (mid same, rid changed)
            moved_new = self._wrap(mid, rid)
            self.bvh.insert(moved_new)
            self.mdx.insert(moved_new)

        # 3) invalidate last and decrement
        self.invalidate_slot(mid, last)
        self.deln(mid=mid)

    # ============================================================
    # queries
    # ============================================================

    def size(self) -> SIZE:
        return (self.p1[0] - self.p0[0], self.p1[1] - self.p0[1], self.p1[2] - self.p0[2])

    def volume(self, mat: str = None) -> int:
        if mat is None:
            total = 0
            for mid in range(MATERIALS.NUM):
                total += self.volume(mat=self.mat.name(mid=mid))
            return total

        mid = int(self.mat.mid(name=mat))
        total = 0
        n = self.nrows(mid=mid)
        arr = self.array[mid]
        for rid in range(n):
            total += ROW.VOLUME(row=arr[rid])
        return total

    def search(self, pos: POS = None) -> Row:
        return self.bvh.search(pos)

    # ============================================================
    # split
    # ============================================================

    def splitrow(self, pos: POS = None, p2: POS = None, mat: str = None) -> REQS:
        if pos is None or p2 is None or mat is None:
            raise ValueError("splitrow requires pos,p2,mat")

        hit = self.search(pos=pos)
        mat0 = self.mat.name(mid=int(hit.mid))

        r0 = ROW.P0(row=hit.row)
        r1 = ROW.P1(row=hit.row)

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

        out, arids = self.reqs(n=27)

        for i, (X0, X1) in enumerate(xs):
            for j, (Y0, Y1) in enumerate(ys):
                for k, (Z0, Z1) in enumerate(zs):
                    if (X1 - X0) <= 0 or (Y1 - Y0) <= 0 or (Z1 - Z0) <= 0:
                        continue

                    center = (i == 1 and j == 1 and k == 1)
                    use_mat = mat if center else mat0

                    newr = self.insert(p0=(X0, Y0, Z0), p1=(X1, Y1, Z1), mat=use_mat)
                    mid_new = int(newr.mid)

                    out[mid_new][arids[mid_new]] = newr.row
                    arids[mid_new] += 1

        self.remove(hit)
        return (out, arids)

    def split1(self, pos: POS = None, mat: str = None) -> REQS:
        if pos is None or mat is None:
            raise ValueError("split1 requires pos,mat")
        p2 = (pos[0] + 1, pos[1] + 1, pos[2] + 1)
        batch, _ = self.splitrow(pos=pos, p2=p2, mat=mat)
        merged, marids = self.merge(rows=batch)
        return (merged, marids)

    def split2(self, p0: POS = None, p1: POS = None, mat: str = None) -> REQS:
        if p0 is None or p1 is None or mat is None:
            raise ValueError("split2 requires p0,p1,mat")

        def intersect(a0: POS, a1: POS, b0: POS, b1: POS):
            q0 = (max(a0[0], b0[0]), max(a0[1], b0[1]), max(a0[2], b0[2]))
            q1 = (min(a1[0], b1[0]), min(a1[1], b1[1]), min(a1[2], b1[2]))
            if q0[0] >= q1[0] or q0[1] >= q1[1] or q0[2] >= q1[2]:
                return None
            return (q0, q1)

        p0, p1 = ROW.SORT(p0=p0, p1=p1)
        if p0[0] >= p1[0] or p0[1] >= p1[1] or p0[2] >= p1[2]:
            return self.reqs(n=0)

        acc: list[list[NDARR]] = [[] for _ in range(MATERIALS.NUM)]

        hit = self.search(pos=p0)
        r0 = ROW.P0(row=hit.row)
        r1 = ROW.P1(row=hit.row)

        hitbox = intersect(p0, p1, r0, r1)
        if hitbox is None:
            return self.reqs(n=0)

        q0, q1 = hitbox

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

        out_arids = {mid: len(acc[mid]) for mid in range(MATERIALS.NUM)}
        n = max(out_arids.values()) if out_arids else 0
        out, arids = self.reqs(n=n)

        for mid in range(MATERIALS.NUM):
            arids[mid] = out_arids[mid]
            for i, rr in enumerate(acc[mid]):
                out[mid][i] = rr

        return (out, arids)

    def split(self, pos: POS = None, pos1: POS = None, mat: str = None) -> REQS:
        if mat is None:
            raise ValueError("material must be specified")
        if pos is None and pos1 is None:
            raise ValueError("either pos or pos1 must be provided")

        if pos is not None and pos1 is not None:
            return self.split2(p0=pos, p1=pos1, mat=mat)
        if pos is not None:
            return self.split1(pos=pos, mat=mat)
        return self.split1(pos=pos1, mat=mat)

    # ============================================================
    # merge
    # ============================================================

    def merge2(self, r0: Row = None, r1: Row = None) -> REQS:
        if r0 is None or r1 is None:
            return self.reqs(n=0)

        mid = int(r0.mid)
        if int(r1.mid) != mid:
            return self.reqs(n=0)

        touch = ROW.MERGE(row0=r0.row, row1=r1.row)
        if touch == (False, False, False):
            return self.reqs(n=0)

        p0 = ROW.SORT(p0=ROW.P0(row=r0.row), p1=ROW.P0(row=r1.row))[0]
        p1 = ROW.SORT(p0=ROW.P1(row=r0.row), p1=ROW.P1(row=r1.row))[1]

        # remove higher rid first (swap-safe)
        if int(r0.rid) > int(r1.rid):
            hi, lo = r0, r1
        else:
            hi, lo = r1, r0

        self.remove(hi)
        self.remove(lo)

        mat_name = self.mat.name(mid=mid)
        newr = self.insert(p0=p0, p1=p1, mat=mat_name)

        out, arids = self.reqs(n=1)
        out[mid][0] = newr.row
        arids[mid] = 1
        return (out, arids)

    def mergeax(self, mat: str = None, axis: int = None) -> REQS:
        if axis is None:
            raise ValueError("mergeax requires axis")
        if mat is None:
            raise ValueError("mergeax requires mat")

        mid = int(self.mat.mid(name=mat))
        start_n = self.nrows(mid=mid)
        out, arids = self.reqs(n=start_n)

        extra = list(range(self.arids[mid] - 1, -1, -1))
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

            r0 = self._wrap(mid, rid)
            r1 = self._wrap(mid, prid)

            created, carids = self.merge2(r0=r0, r1=r1)
            if carids[mid] > 0:
                out[mid][arids[mid]] = created[mid][0]
                arids[mid] += 1

                new_rid = self.arids[mid] - 1
                extra.append(new_rid)

                if rid < self.arids[mid]:
                    seen.discard(rid)
                    extra.append(rid)

        return (out, arids)

    def mergemat(self, mat: str = None) -> REQS:
        if mat is None:
            raise ValueError("mergemat requires mat")

        mid = int(self.mat.mid(name=mat))
        start_n = self.nrows(mid=mid)
        out, arids = self.reqs(n=start_n)

        for ax in range(3):
            while True:
                created, carids = self.mergeax(mat=mat, axis=ax)
                if carids[mid] <= 0:
                    break
                for i in range(carids[mid]):
                    out[mid][arids[mid]] = created[mid][i]
                    arids[mid] += 1

        return (out, arids)

    def mergeall(self) -> REQS:
        out, arids = self.reqs(n=self.total)
        for mat in self.mat.names():
            created, carids = self.mergemat(mat=mat)
            for mid in range(MATERIALS.NUM):
                for i in range(carids[mid]):
                    out[mid][arids[mid]] = created[mid][i]
                    arids[mid] += 1
        return (out, arids)

    def mergerows(self, rows: NDARR = None) -> REQS:
        # Keeping your existing approach; can be optimized later.
        # This function expects "rows" as an NDARR bundle of rowdata.
        if rows is None:
            return self.reqs(n=0)

        mids_present: set[int] = set()
        for mid in range(rows.shape[0]):
            for i in range(rows.shape[1]):
                if rows[mid][i][*ROW.IDS_RID] != ROW.SENTINEL:
                    mids_present.add(mid)
                    break

        worst = 0
        for mid in mids_present:
            worst += self.nrows(mid=mid)

        out, arids = self.reqs(n=worst)

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

                    r0 = self._wrap(mid, rid)
                    r1 = self._wrap(mid, prid)

                    created, carids = self.merge2(r0=r0, r1=r1)
                    if carids[mid] > 0:
                        out[mid][arids[mid]] = created[mid][0]
                        arids[mid] += 1
                        merged_this_round += 1

                        new_rid = self.arids[mid] - 1
                        extra.append((mid, new_rid))

                        seen.discard((mid, rid))
                        extra.append((mid, rid))

            if merged_this_round == 0:
                break

        return (out, arids)

    def merge(self, rows: NDARR = None) -> REQS:
        if rows is None:
            return self.mergeall()
        return self.mergerows(rows=rows)

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        n = self.nrows(mat="STONE")
        return f"ROWS(shape={self.shape}, nbytes={self.nbytes}, gbytes={self.gbytes:.3f} with {n} valid rows)"
