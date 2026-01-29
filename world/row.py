from __future__ import annotations
import stat
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass



import numpy as np
from numpy.typing import NDArray


from utils.types import SIZE, POS
from world.materials import Material, Materials





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
    IDS_X0 = (0, 0)
    IDS_Y0 = (0, 1)
    IDS_Z0 = (0, 2)

    # POSITIONS (MAX) — stored in row 1
    IDS_X1 = (1, 0)
    IDS_Y1 = (1, 1)
    IDS_Z1 = (1, 2)

    # DIMENSIONS — stored in row 2
    IDS_DX = (2, 0)
    IDS_DY = (2, 1)
    IDS_DZ = (2, 2)

    # METADATA — stored in row 3
    IDS_ID    = (3, 0)
    IDS_MAT   = (3, 1)
    IDS_FLAGS = (3, 2)

    ENCODE_DIRTY        = DTYPE(1 << 0)
    ENCODE_ALIVE        = DTYPE(1 << 1)
    ENCODE_SOLID        = DTYPE(1 << 2)
    ENCODE_DESTRUCTABLE = DTYPE(1 << 3)
    ENCODE_VISIBLE      = DTYPE(1 << 4)

    SENTINEL = np.iinfo(DTYPE).max
    ARRAY: NDArray[DTYPE] = np.zeros(SHAPE, dtype=DTYPE)
    for i in range(4):
        for j in range(4):
            ARRAY[i, j] = SENTINEL  # initialize all to -1 -> invalid
    _ID = 0
    
    @staticmethod # get min position (x0, y0, z0)   
    def P0(row:NDArray[DTYPE]=None) -> POS:
        return (int(row[*ROW.IDS_X0]), int(row[*ROW.IDS_Y0]), int(row[*ROW.IDS_Z0]))
    
    @staticmethod # get max position (x1, y1, z1)
    def P1(row:NDArray[DTYPE]=None) -> POS:
        return (int(row[*ROW.IDS_X1]), int(row[*ROW.IDS_Y1]), int(row[*ROW.IDS_Z1]))
    
    @staticmethod # get size (dx, dy, dz)
    def SIZE(row:NDArray[DTYPE]=None) -> SIZE:
        return (int(row[*ROW.IDS_DX]), int(row[*ROW.IDS_DY]), int(row[*ROW.IDS_DZ]))
    
    @staticmethod # get material id
    def MID(row:NDArray[DTYPE]=None) -> int:
        return int(row[*ROW.IDS_MAT])
    
    @staticmethod # get meterial string name
    def MAT(row:NDArray[DTYPE]=None) -> str:
        return Materials.id2name[ROW.MID(row=row)]
    
    @staticmethod # get row id
    def RID(row:NDArray[DTYPE]=None) -> int:
        return int(row[*ROW.IDS_ID])
    
    @staticmethod # get flags
    def FLAGS(row:NDArray[DTYPE]=None) -> tuple[bool, bool, bool, bool, bool]:
        flags: int = int(row[*ROW.IDS_FLAGS])
        dirty, alive, solid, destr, visib = ROW.DECODE(flags=flags)
        return (dirty, alive, solid, destr, visib)
    
    @staticmethod # get volume (dx * dy * dz)
    def VOLUME(row:NDArray[DTYPE]=None) -> int:
        dx, dy, dz = ROW.SIZE(row=row)
        return dx * dy * dz

    @staticmethod # make a copy of the template array
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
        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)
        return (
            (x0 <= x < x1) and
            (y0 <= y < y1) and
            (z0 <= z < z1)
        )
    
    @staticmethod
    def MERGE(row0: NDArray[DTYPE]=None, row1: NDArray[DTYPE]=None) -> tuple[bool, bool, bool]:
        if row0[*ROW.IDS_MAT] != row1[*ROW.IDS_MAT]:
            return (False, False, False)

        x0a, y0a, z0a = ROW.P0(row=row0)
        x1a, y1a, z1a = ROW.P1(row=row0)
        x0b, y0b, z0b = ROW.P0(row=row1)
        x1b, y1b, z1b = ROW.P1(row=row1)
        p00 = (x0a, y0a, z0a)
        p01 = (x1a, y1a, z1a)
        p10 = (x0b, y0b, z0b)
        p11 = (x1b, y1b, z1b)

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
            
        if sum(touching) == 1 and sum(overlaps) == 2:
            return tuple(touching)  # (x_touch, y_touch, z_touch)

        return (False, False, False)
    

    @staticmethod
    def ENCODE(dirty:bool=None, alive:bool=None, solid:bool=None, destructable:bool=None, visible:bool=None) -> int:
        f: int = 0
        if dirty:
            f |= int(ROW.ENCODE_DIRTY)
        if alive:
            f |= int(ROW.ENCODE_ALIVE)
        if solid:
            f |= int(ROW.ENCODE_SOLID)
        if destructable:
            f |= int(ROW.ENCODE_DESTRUCTABLE)
        if visible:
            f |= int(ROW.ENCODE_VISIBLE)
        return f
    
    @staticmethod
    def DECODE(flags) -> tuple[bool, bool, bool, bool, bool]:
        f: int = int(flags)

        dirty = (f & int(ROW.ENCODE_DIRTY)) != 0
        alive = (f & int(ROW.ENCODE_ALIVE)) != 0
        solid = (f & int(ROW.ENCODE_SOLID)) != 0
        destr = (f & int(ROW.ENCODE_DESTRUCTABLE)) != 0
        visib = (f & int(ROW.ENCODE_VISIBLE)) != 0
        return dirty, alive, solid, destr, visib








                

    @staticmethod
    def new(p0:POS=None, p1:POS=None, mat:str=None, rid:int=None, dirty:bool=True, alive:bool=True) -> NDArray[DTYPE]:
        p0, p1 = ROW.SORT(p0=ROW.CLIP(pos=p0), p1=ROW.CLIP(pos=p1))
        mat: Material = Material(name=mat)
        flags: int = ROW.ENCODE(dirty=dirty, alive=alive, solid=mat.issolid(), destructable=not mat.isindestructible(), visible=not mat.isinvisible())
        
        copy: NDArray[ROW.DTYPE] = ROW.COPY()

        # POS0
        copy[*ROW.IDS_X0]    = np.uint64(p0[0])
        copy[*ROW.IDS_Y0]    = np.uint64(p0[1])
        copy[*ROW.IDS_Z0]    = np.uint64(p0[2])
        # POS1
        copy[*ROW.IDS_X1]    = np.uint64(p1[0])
        copy[*ROW.IDS_Y1]    = np.uint64(p1[1])
        copy[*ROW.IDS_Z1]    = np.uint64(p1[2])
        # SIZE
        copy[*ROW.IDS_DX]    = np.uint64(p1[0] - p0[0])
        copy[*ROW.IDS_DY]    = np.uint64(p1[1] - p0[1])
        copy[*ROW.IDS_DZ]    = np.uint64(p1[2] - p0[2])
        # METADATA
        copy[*ROW.IDS_ID]    = np.uint64(rid)       # stores now the row index within material array instead of global unique id
        copy[*ROW.IDS_MAT]   = np.uint64(mat.id)
        copy[*ROW.IDS_FLAGS] = np.uint64(flags)

        if any(v < 0 for v in (copy[*ROW.IDS_DX], copy[*ROW.IDS_DY], copy[*ROW.IDS_DZ])):
            raise ValueError("p1 must be greater than or equal to p0 on all axes")
        if any(v < 0 for v in (copy[*ROW.IDS_X0], copy[*ROW.IDS_Y0], copy[*ROW.IDS_Z0])):
            raise ValueError("positions must be non-negative")
        return copy
    
    