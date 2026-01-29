from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.rows import ROWS



from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, Optional, Set, Tuple

from world.row import ROW

# rid locator
Loc = Tuple[int, int]  # (mid, rid)

# Face keys:
# We include mid (material index) so we can merge per-material quickly.
# The spans must match exactly on the other two axes.
FaceKey = Tuple[int, int, int, int, int, int]  # (mid, a0, a1, b0, b1, face_coord)


@dataclass
class _RowFaces:
    # store the 6 keys so we can unregister quickly without recomputing
    x0: FaceKey
    x1: FaceKey
    y0: FaceKey
    y1: FaceKey
    z0: FaceKey
    z1: FaceKey


class MDX:
    """
    Tracks adjacency candidates for merges using face hashing.

    For each axis we maintain:
      neg[axis][key] -> set of (mid,rid) with face at MIN along that axis
      pos[axis][key] -> set of (mid,rid) with face at MAX along that axis

    A merge along X exists when:
      pos[X][(mid, y0,y1,z0,z1, x)] intersects neg[X][(mid, y0,y1,z0,z1, x)]
    """

    AX_X = 0
    AX_Y = 1
    AX_Z = 2

    def __init__(self, rows:ROWS=None) -> None:
        self.rows = rows
        # axis -> key -> set(loc)
        self.neg: Tuple[DefaultDict[FaceKey, Set[Loc]], ...] = (
            defaultdict(set), defaultdict(set), defaultdict(set)
        )
        self.pos: Tuple[DefaultDict[FaceKey, Set[Loc]], ...] = (
            defaultdict(set), defaultdict(set), defaultdict(set)
        )

        # (mid,rid) -> stored face keys (for O(1) unregister)
        self._faces: Dict[Loc, _RowFaces] = {}

    # ---------------------------
    # key construction
    # ---------------------------
    @staticmethod
    def _faces_for(mid: int, row) -> _RowFaces:
        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)
        # axis X: spans are (y0,y1,z0,z1), face coord is x0 or x1
        kx0: FaceKey = (mid, y0, y1, z0, z1, x0)
        kx1: FaceKey = (mid, y0, y1, z0, z1, x1)
        # axis Y: spans are (x0,x1,z0,z1), face coord is y0 or y1
        ky0: FaceKey = (mid, x0, x1, z0, z1, y0)
        ky1: FaceKey = (mid, x0, x1, z0, z1, y1)
        # axis Z: spans are (x0,x1,y0,y1), face coord is z0 or z1
        kz0: FaceKey = (mid, x0, x1, y0, y1, z0)
        kz1: FaceKey = (mid, x0, x1, y0, y1, z1)
        return _RowFaces(x0=kx0, x1=kx1, y0=ky0, y1=ky1, z0=kz0, z1=kz1)

    # ---------------------------
    # register / unregister
    # ---------------------------
    def insert(self, row=None) -> None:
        mid = self.rows.mats.name2idx[ROW.MAT(row=row)]
        rid = ROW.RID(row=row)
        loc = (mid, rid)
        faces = self._faces_for(mid, row)
        self._faces[loc] = faces

        self.neg[self.AX_X][faces.x0].add(loc)
        self.pos[self.AX_X][faces.x1].add(loc)

        self.neg[self.AX_Y][faces.y0].add(loc)
        self.pos[self.AX_Y][faces.y1].add(loc)

        self.neg[self.AX_Z][faces.z0].add(loc)
        self.pos[self.AX_Z][faces.z1].add(loc)

    def remove(self, mat:str=None, rid:int=None) -> None:
        mid = self.rows.mats.name2idx[mat]
        loc = (mid, rid)
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
    def _discard(m: DefaultDict[FaceKey, Set[Loc]], key: FaceKey, loc: Loc) -> None:
        s = m.get(key)
        if not s:
            return
        s.discard(loc)
        if not s:
            # keep dict small
            del m[key]

    # ---------------------------
    # rid move helper (swap-delete)
    # ---------------------------
    def move_rid(self, mid: int, old_rid: int, new_rid: int, row) -> None:
        self.remove(mat=self.rows.mats.idx2name[mid], rid=old_rid)
        self.insert(row=row)

    # ---------------------------
    # partner query
    # ---------------------------
    def find_partner(self, mid: int, rid: int, axis: int) -> Optional[Loc]:
        """
        Finds any merge partner for (mid,rid) along given axis.
        Returns (mid, rid2) or None.
        """
        loc = (mid, rid)
        faces = self._faces.get(loc)
        if faces is None:
            return None

        if axis == self.AX_X:
            # partner has x0 == our x1, same yz span
            key = faces.x1
            candidates = self.neg[self.AX_X].get(key)
        elif axis == self.AX_Y:
            key = faces.y1
            candidates = self.neg[self.AX_Y].get(key)
        elif axis == self.AX_Z:
            key = faces.z1
            candidates = self.neg[self.AX_Z].get(key)
        else:
            raise ValueError("axis must be 0,1,2")

        if not candidates:
            return None

        # return any candidate that isn't self
        for c in candidates:
            if c != loc:
                return c
        return None
