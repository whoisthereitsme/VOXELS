from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass



import numpy as np
from numpy.typing import NDArray


from utils.types import SIZE, POS
from world.materials import Material





class ROW:
    DTYPE = np.uint64
    SHAPE = (4, 4)
    NBITS = DTYPE(0).nbytes * 8                      # -> 64 bits

    XBITS = 20
    YBITS = 20
    ZBITS = 16
    if XBITS + YBITS + ZBITS + 1 > NBITS:
        raise ValueError("bit allocation error")

    XMIN = 0
    YMIN = 0
    ZMIN = 0
    XMAX = 2**XBITS
    YMAX = 2**YBITS
    ZMAX = 2**ZBITS
    NMAX = XMAX * YMAX * ZMAX


    # POSITIONS (MIN) — stored in row 0
    X0 = (0, 0)
    Y0 = (0, 1)
    Z0 = (0, 2)

    # POSITIONS (MAX) — stored in row 1
    X1 = (1, 0)
    Y1 = (1, 1)
    Z1 = (1, 2)

    # DIMENSIONS — stored in row 2
    DX = (2, 0)
    DY = (2, 1)
    DZ = (2, 2)

    # METADATA — stored in row 3
    ID    = (3, 0)
    MAT   = (3, 1)
    FLAGS = (3, 2)

    DIRTY        = DTYPE(1 << 0)
    ALIVE        = DTYPE(1 << 1)
    SOLID        = DTYPE(1 << 2)
    DESTRUCTABLE = DTYPE(1 << 3)
    VISIBLE      = DTYPE(1 << 4)

    SENTINEL = np.iinfo(DTYPE).max
    ARRAY: NDArray[DTYPE] = np.zeros(SHAPE, dtype=DTYPE)
    for i in range(4):
        for j in range(4):
            ARRAY[i, j] = SENTINEL  # initialize all to -1 -> invalid
    _ID = 0
    
    @staticmethod
    def P0(row:NDArray[DTYPE]=None) -> POS:
        return (int(row[*ROW.X0]), int(row[*ROW.Y0]), int(row[*ROW.Z0]))
    
    @staticmethod
    def P1(row:NDArray[DTYPE]=None) -> POS:
        return (int(row[*ROW.X1]), int(row[*ROW.Y1]), int(row[*ROW.Z1]))
    
    @staticmethod
    def SIZE(row:NDArray[DTYPE]=None) -> SIZE:
        return (int(row[*ROW.DX]), int(row[*ROW.DY]), int(row[*ROW.DZ]))
    
    @staticmethod
    def VOLUME(row:NDArray[DTYPE]=None) -> int:
        dx, dy, dz = ROW.SIZE(row=row)
        return dx * dy * dz

    @staticmethod
    def COPY() -> NDArray[DTYPE]:
        return np.copy(ROW.ARRAY)
    
    @staticmethod
    def CLIP(pos:POS=None) -> POS:
        x, y, z = pos
        cx = min(max(x, ROW.XMIN), ROW.XMAX - 1)
        cy = min(max(y, ROW.YMIN), ROW.YMAX - 1)
        cz = min(max(z, ROW.ZMIN), ROW.ZMAX - 1)
        pos: POS = (cx, cy, cz)
        return pos
    
    @staticmethod
    def SORT(p0:POS=None, p1:POS=None) -> tuple[POS, POS]:
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        sx0, sx1 = (min(x0, x1), max(x0, x1))
        sy0, sy1 = (min(y0, y1), max(y0, y1))
        sz0, sz1 = (min(z0, z1), max(z0, z1))
        p0: POS = (sx0, sy0, sz0)
        p1: POS = (sx1, sy1, sz1)
        return (p0, p1)
    
    @staticmethod
    def CONTAINS(row: NDArray[DTYPE], pos: POS) -> bool:
        x, y, z = pos
        return (
            int(row[*ROW.X0]) <= x < int(row[*ROW.X1]) and
            int(row[*ROW.Y0]) <= y < int(row[*ROW.Y1]) and
            int(row[*ROW.Z0]) <= z < int(row[*ROW.Z1])
        )
    
    @staticmethod
    def MERGE(row0: NDArray[DTYPE]=None, row1: NDArray[DTYPE]=None) -> tuple[bool, bool, bool]:
        if row0[*ROW.MAT] != row1[*ROW.MAT]:
            return (False, False, False)

        p00 = (row0[*ROW.X0], row0[*ROW.Y0], row0[*ROW.Z0])
        p01 = (row0[*ROW.X1], row0[*ROW.Y1], row0[*ROW.Z1])
        p10 = (row1[*ROW.X0], row1[*ROW.Y0], row1[*ROW.Z0])
        p11 = (row1[*ROW.X1], row1[*ROW.Y1], row1[*ROW.Z1])

        def overlap(a0:int=None, a1:int=None, b0:int=None, b1:int=None) -> bool: return a0 < b1 and b0 < a1
        def touches(a0:int=None, a1:int=None, b0:int=None, b1:int=None) -> bool: return a1 == b0 or b1 == a0

        touching = [False, False, False]
        overlaps = [False, False, False]

        for i in range(3):
            if overlap(a0=p00[i], a1=p01[i], b0=p10[i], b1=p11[i]):
                overlaps[i] = True
            elif touches(a0=p00[i], a1=p01[i], b0=p10[i], b1=p11[i]):
                touching[i] = True
            else:
                return (False, False, False)  # separated on this axis

        # mergeable ⇔ exactly one touching axis and two overlapping axes
        if sum(touching) == 1 and sum(overlaps) == 2:
            return tuple(touching)  # (x_touch, y_touch, z_touch)

        return (False, False, False)
                

    @staticmethod
    def new(p0:POS=None, p1:POS=None, mat:str=None, rid:int=None, dirty:bool=True, alive:bool=True) -> NDArray[DTYPE]:
        p0, p1 = ROW.SORT(p0=ROW.CLIP(pos=p0), p1=ROW.CLIP(pos=p1))
        mat: Material = Material(name=mat)
        flags: int = ROW.encode(dirty=dirty, alive=alive, solid=mat.issolid(), destructable=not mat.isindestructible(), visible=not mat.isinvisible())
        
        copy: NDArray[ROW.DTYPE] = ROW.COPY()

        # POS0
        copy[*ROW.X0]    = np.uint64(p0[0])
        copy[*ROW.Y0]    = np.uint64(p0[1])
        copy[*ROW.Z0]    = np.uint64(p0[2])
        # POS1
        copy[*ROW.X1]    = np.uint64(p1[0])
        copy[*ROW.Y1]    = np.uint64(p1[1])
        copy[*ROW.Z1]    = np.uint64(p1[2])
        # SIZE
        copy[*ROW.DX]    = np.uint64(p1[0] - p0[0])
        copy[*ROW.DY]    = np.uint64(p1[1] - p0[1])
        copy[*ROW.DZ]    = np.uint64(p1[2] - p0[2])
        # METADATA
        copy[*ROW.ID]    = np.uint64(rid)       # stores now the row index within material array instead of global unique id
        copy[*ROW.MAT]   = np.uint64(mat.id)
        copy[*ROW.FLAGS] = np.uint64(flags)

        if any(v < 0 for v in (copy[*ROW.DX], copy[*ROW.DY], copy[*ROW.DZ])):
            raise ValueError("p1 must be greater than or equal to p0 on all axes")
        if any(v < 0 for v in (copy[*ROW.X0], copy[*ROW.Y0], copy[*ROW.Z0])):
            raise ValueError("positions must be non-negative")
        return copy
    
    @staticmethod
    def encode(dirty:bool=None, alive:bool=None, solid:bool=None, destructable:bool=None, visible:bool=None) -> int:
        f: int = 0
        if dirty:
            f |= int(ROW.DIRTY)
        if alive:
            f |= int(ROW.ALIVE)
        if solid:
            f |= int(ROW.SOLID)
        if destructable:
            f |= int(ROW.DESTRUCTABLE)
        if visible:
            f |= int(ROW.VISIBLE)
        return f
    
    @staticmethod
    def decode(flags) -> tuple[bool, bool, bool, bool, bool]:
        f: int = int(flags)

        dirty = (f & int(ROW.DIRTY)) != 0
        alive = (f & int(ROW.ALIVE)) != 0
        solid = (f & int(ROW.SOLID)) != 0
        destr = (f & int(ROW.DESTRUCTABLE)) != 0
        visib = (f & int(ROW.VISIBLE)) != 0

        return dirty, alive, solid, destr, visib







