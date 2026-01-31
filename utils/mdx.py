from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.rows import ROWS
    


from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, Optional, Set, Tuple

from world.row import ROW, NDArray

Loc = Tuple[int, int]  # (mid, rid)
FACE = Tuple[int, int, int, int, int, int]  # (mid, a0, a1, b0, b1, face_coord)
BUCK = DefaultDict[FACE, Set[Loc]]  # face_key -> set of (mid, rid)
FACES = Tuple[FACE, FACE]  # (max_face, min_face)  # our faces, in search order
BUCKS = Tuple[BUCK, BUCK]  # (neg_bucket, pos_bucket)

@dataclass
class ROWFACES:
    x0: FACE
    x1: FACE
    y0: FACE
    y1: FACE
    z0: FACE
    z1: FACE

    @property
    def xfaces(self) -> FACES:
        return (self.x1, self.x0)

    @property
    def yfaces(self) -> FACES:
        return (self.y1, self.y0)

    @property
    def zfaces(self) -> FACES:
        return (self.z1, self.z0)

    def faces(self, ax:int=None) -> FACES:
        if ax not in [0, 1, 2]:
            raise ValueError("[VALUE ERROR] ROWFACES.faces() ax must be 0,1,2. provided axis:", ax)
        return (self.xfaces, self.yfaces, self.zfaces)[ax]


class MDX:
    AX_X = 0
    AX_Y = 1
    AX_Z = 2
    ALLAXIS = (AX_X, AX_Y, AX_Z)

    def __init__(self, rows:ROWS=None) -> None:
        self.rows = rows
        self.init()

    def init(self) -> None:
        self.neg: Tuple[BUCK, ...] = (defaultdict(set), defaultdict(set), defaultdict(set))
        self.pos: Tuple[BUCK, ...] = (defaultdict(set), defaultdict(set), defaultdict(set))
        self._faces: Dict[Loc, ROWFACES] = {}

    def faces(self, mid:int=None, row:NDArray[ROW.DTYPE]=None) -> ROWFACES:
        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)

        kx0: FACE = (mid, y0, y1, z0, z1, x0)
        kx1: FACE = (mid, y0, y1, z0, z1, x1)
        ky0: FACE = (mid, x0, x1, z0, z1, y0)
        ky1: FACE = (mid, x0, x1, z0, z1, y1)
        kz0: FACE = (mid, x0, x1, y0, y1, z0)
        kz1: FACE = (mid, x0, x1, y0, y1, z1)
        return ROWFACES(x0=kx0, x1=kx1, y0=ky0, y1=ky1, z0=kz0, z1=kz1)

    def insert(self, row:NDArray[ROW.DTYPE]=None) -> None:
        mid = self.rows.mats.name2idx[ROW.MAT(row=row)]
        rid = ROW.RID(row=row)
        loc: Loc = (mid, rid)
        faces = self.faces(mid=mid, row=row)
        self._faces[loc] = faces

        self.neg[self.AX_X][faces.x0].add(loc)
        self.pos[self.AX_X][faces.x1].add(loc)
        self.neg[self.AX_Y][faces.y0].add(loc)
        self.pos[self.AX_Y][faces.y1].add(loc)
        self.neg[self.AX_Z][faces.z0].add(loc)
        self.pos[self.AX_Z][faces.z1].add(loc)

    def remove(self, mat:str=None, rid:int=None) -> None:
        mid = self.rows.mats.name2idx[mat]
        loc: Loc = (mid, rid)
        faces: ROWFACES = self._faces.pop(loc, None)
        if faces is None:
            return

        self.discard(m=self.neg[self.AX_X], key=faces.x0, loc=loc)
        self.discard(m=self.pos[self.AX_X], key=faces.x1, loc=loc)
        self.discard(m=self.neg[self.AX_Y], key=faces.y0, loc=loc)
        self.discard(m=self.pos[self.AX_Y], key=faces.y1, loc=loc)
        self.discard(m=self.neg[self.AX_Z], key=faces.z0, loc=loc)
        self.discard(m=self.pos[self.AX_Z], key=faces.z1, loc=loc)

    def discard(self, m:BUCK=None, key:FACE=None, loc:Loc=None) -> None:
        s: Set[Loc] = m.get(key)
        if not s:
            return
        s.discard(loc)
        if not s:
            del m[key]

    def search(self, mid:int=None, rid:int=None, axis:int=None) -> Optional[Loc]:
        if mid is None or rid is None or axis is None:
            raise ValueError("mid, rid, and axis must be provided")
        loc: Loc = (mid, rid)
        rowfaces: ROWFACES = self._faces.get(loc)
        if rowfaces is None:
            return None

        def search(faces:FACES=None, bucks:BUCKS=None) -> Optional[Loc]:
            for face, buck in zip(faces, bucks):
                buck: BUCK = buck
                face: FACE = face
                candidates = buck.get(face)
                if not candidates:
                    continue
                for c in candidates:
                    if c != loc:
                        return c
            return None

        faces: FACES = rowfaces.faces(ax=axis) 
        bucks: BUCKS = (self.neg[axis], self.pos[axis])

        return search(faces=faces, bucks=bucks)