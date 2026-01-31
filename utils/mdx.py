# utils/mdx.py
from __future__ import annotations
from typing import TYPE_CHECKING, DefaultDict, Dict, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

if TYPE_CHECKING:
    from world.rows import ROWS

from world.row import ROW
from utils.types import NDARR, Row

LOC = Tuple[int, int]  # (mid, rid)
FACE = Tuple[int, int, int, int, int, int]
BUCK = DefaultDict[FACE, Set[LOC]]  # face_key -> set of LOCs
FACES = Tuple[FACE, FACE]           # (pos_face, neg_face) for search order
BUCKS = Tuple[BUCK, BUCK]           # (neg_bucket, pos_bucket)


@dataclass(slots=True)
class Faces:
    x0: FACE
    x1: FACE
    y0: FACE
    y1: FACE
    z0: FACE
    z1: FACE

    def faces_for_axis(self, ax: int) -> FACES:
        if ax == 0:
            return (self.x1, self.x0)
        if ax == 1:
            return (self.y1, self.y0)
        if ax == 2:
            return (self.z1, self.z0)
        raise ValueError("axis must be 0,1,2")


class MDX:
    AX_X = 0
    AX_Y = 1
    AX_Z = 2
    ALLAXIS = (AX_X, AX_Y, AX_Z)

    def __init__(self, rows: "ROWS" = None) -> None:
        self.rows = rows
        self.init()

    def init(self) -> None:
        self.neg: Tuple[BUCK, BUCK, BUCK] = (defaultdict(set), defaultdict(set), defaultdict(set))
        self.pos: Tuple[BUCK, BUCK, BUCK] = (defaultdict(set), defaultdict(set), defaultdict(set))
        self._faces: Dict[LOC, Faces] = {}


    def _build_faces(self, mid: int, row: NDARR) -> Faces:
        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)

        fx0: FACE = (mid, y0, y1, z0, z1, x0)
        fx1: FACE = (mid, y0, y1, z0, z1, x1)

        fy0: FACE = (mid, x0, x1, z0, z1, y0)
        fy1: FACE = (mid, x0, x1, z0, z1, y1)

        fz0: FACE = (mid, x0, x1, y0, y1, z0)
        fz1: FACE = (mid, x0, x1, y0, y1, z1)

        return Faces(x0=fx0, x1=fx1, y0=fy0, y1=fy1, z0=fz0, z1=fz1)


    def insert(self, row: Row=None) -> None:
        mid, rid, row = int(row.mid), int(row.rid), row.row
        loc: LOC = (mid, rid)

        faces = self._build_faces(mid=mid, row=row)
        self._faces[loc] = faces

        self.neg[self.AX_X][faces.x0].add(loc)
        self.pos[self.AX_X][faces.x1].add(loc)
        self.neg[self.AX_Y][faces.y0].add(loc)
        self.pos[self.AX_Y][faces.y1].add(loc)
        self.neg[self.AX_Z][faces.z0].add(loc)
        self.pos[self.AX_Z][faces.z1].add(loc)


    def remove(self, row: Row=None) -> None:
        mid, rid = int(row.mid), int(row.rid)
        loc: LOC = (mid, rid)

        faces = self._faces.pop(loc, None)
        if faces is None:
            return

        self._discard(self.neg[self.AX_X], faces.x0, loc)
        self._discard(self.pos[self.AX_X], faces.x1, loc)

        self._discard(self.neg[self.AX_Y], faces.y0, loc)
        self._discard(self.pos[self.AX_Y], faces.y1, loc)

        self._discard(self.neg[self.AX_Z], faces.z0, loc)
        self._discard(self.pos[self.AX_Z], faces.z1, loc)

    @staticmethod
    def _discard(m: BUCK, key: FACE, loc: LOC) -> None:
        s = m.get(key)
        if not s:
            return
        s.discard(loc)
        if not s:
            del m[key]


    def search(self, r: Row, axis: int) -> Optional[Row]:
        """
        Find ONE merge-candidate neighbor (same material) touching on `axis`.

        Returns:
            Row(mid, rid, row_view) or None
        """
        if axis not in (0, 1, 2):
            raise ValueError("axis must be 0,1,2")

        mid, rid = int(r.mid), int(r.rid)
        loc: LOC = (mid, rid)

        faces = self._faces.get(loc)
        if faces is None:
            return None

        face_pos, face_neg = faces.faces_for_axis(axis)
        bucks: BUCKS = (self.neg[axis], self.pos[axis])

        # Try +face then -face (or whatever order faces_for_axis returns)
        for face_key, bucket in ((face_pos, bucks[0]), (face_neg, bucks[1])):
            candidates = bucket.get(face_key)
            if not candidates:
                continue

            # return the first other loc
            for (pmid, prid) in candidates:
                if (pmid, prid) != loc:
                    row = self.rows.array[int(pmid)][int(prid)]
                    return Row(mid=int(pmid), rid=int(prid), row=row)

        return None
