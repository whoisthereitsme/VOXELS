from __future__ import annotations
import stat
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

from utils.types import NDARR

import numpy as np


from utils.types import SIZE, POS
from world.materials import Material, Materials





class ROW:
    """
    PRIVATE VARIABLES!
    NOTES:
        - use the static methods to get stuff done!
        - do not acces these variables directly!
    PURPOSE:
        - defines the keys and structure of a ROW in the world ROWS array
    STRUCTURE:
        - each ROW is a 4x4 numpy uint64 array
        - row 0: min positions (x0, y0, z0)
        - row 1: max positions (x1, y1, z1)
        - row 2: dimensions (dx, dy, dz)
        - row 3: metadata (id, mid, flags)
    USAGE:
        - use the static methods to create, read, and manipulate ROWs
    """
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


    # POSITIONS (MIN) — stored in row 0 (NOT FOR DIRECT USE)
    IDS_X0 = (0, 0)
    IDS_Y0 = (0, 1)
    IDS_Z0 = (0, 2)

    # POSITIONS (MAX) — stored in row 1 (NOT FOR DIRECT USE)
    IDS_X1 = (1, 0)
    IDS_Y1 = (1, 1)
    IDS_Z1 = (1, 2)

    # DIMENSIONS — stored in row 2 (NOT FOR DIRECT USE)
    IDS_DX = (2, 0)
    IDS_DY = (2, 1)
    IDS_DZ = (2, 2)

    # METADATA — stored in row 3 (NOT FOR DIRECT USE)
    IDS_RID    = (3, 0)
    IDS_MID   = (3, 1)
    IDS_FLAGS = (3, 2)

    # ENCODED FLAGS (NOT FOR DIRECT USE)
    ENCODE_DIRTY        = DTYPE(1 << 0)
    ENCODE_ALIVE        = DTYPE(1 << 1)
    ENCODE_SOLID        = DTYPE(1 << 2)
    ENCODE_DESTRUCTABLE = DTYPE(1 << 3)
    ENCODE_VISIBLE      = DTYPE(1 << 4)

    SENTINEL = np.iinfo(DTYPE).max
    ARRAY: NDARR = np.zeros(SHAPE, dtype=DTYPE)
    for i in range(4):
        for j in range(4):
            ARRAY[i, j] = SENTINEL  # initialize all to -1 -> invalid
    _ID = 0

    """
    PRIVATE VARIABLES END 
    """

    @staticmethod
    def X0(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: x0 position
        """
        return row[*ROW.IDS_X0]
    
    @staticmethod
    def Y0(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: y0 position
        """
        return row[*ROW.IDS_Y0]
    
    @staticmethod
    def Z0(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: z0 position
        """
        return row[*ROW.IDS_Z0]
    
    @staticmethod
    def X1(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: x1 position
        """
        return row[*ROW.IDS_X1]
    
    @staticmethod
    def Y1(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: y1 position
        """
        return row[*ROW.IDS_Y1]
    
    @staticmethod
    def Z1(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: z1 position
        """
        return row[*ROW.IDS_Z1]
    
    @staticmethod
    def DX(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: dx size
        """
        return row[*ROW.IDS_DX]
    
    @staticmethod
    def DY(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: dy size
        """
        return row[*ROW.IDS_DY]
    
    @staticmethod
    def DZ(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: dz size
        """
        return row[*ROW.IDS_DZ]
    
    @staticmethod # get min position (x0, y0, z0)  
    def P0(row:NDARR=None) -> POS:
        """
        PUBLIC!
        RETURN: (x0, y0, z0) == p0
        """
        return (ROW.X0(row=row), ROW.Y0(row=row), ROW.Z0(row=row))
    @staticmethod # get max position (x1, y1, z1)
    def P1(row:NDARR=None) -> POS:
        """
        PUBLIC!
        RETURN: (x1, y1, z1) == p1
        """
        return (ROW.X1(row=row), ROW.Y1(row=row), ROW.Z1(row=row))
    
    @staticmethod # get size (dx, dy, dz)
    def SIZE(row:NDARR=None) -> SIZE:
        """
        PUBLIC!
        RETURN: (dx, dy, dz) == size
        """
        return (ROW.DX(row=row), ROW.DY(row=row), ROW.DZ(row=row))
    
    @staticmethod # get material id
    def MID(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: material id integer (Material ID)
        """
        return row[*ROW.IDS_MID]
    
    @staticmethod # get meterial string name
    def MAT(row:NDARR=None) -> str:
        """
        PUBLIC!
        RETURN: material name string (Material Name)
        """
        return Materials.name(mid=ROW.MID(row=row))
    
    @staticmethod # get row id
    def RID(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: row unique id integer (Row ID)
        """
        return row[*ROW.IDS_RID]
    
    @staticmethod # get flags
    def FLAGS(row:NDARR=None) -> tuple[bool, bool, bool, bool, bool]:
        """
        PUBLIC!
        RETURN: tuple of flags (dirty, alive, solid, destructable, visible)
        """
        flags: int = row[*ROW.IDS_FLAGS]
        dirty, alive, solid, destr, visib = ROW.DECODE(flags=flags)
        return (dirty, alive, solid, destr, visib)
    
    @staticmethod # get volume (dx * dy * dz)
    def VOLUME(row:NDARR=None) -> int:
        """
        PUBLIC!
        RETURN: volume (dx * dy * dz)
        """
        dx, dy, dz = ROW.SIZE(row=row)
        return dx * dy * dz

    @staticmethod
    def COPY() -> NDARR:
        """
        PUBLIC!
        RETURN: a copy of the ROW.ARRAY template
        USAGE: use this to create new rows
        """
        return np.copy(ROW.ARRAY)
    
    @staticmethod
    def CLIP(pos:POS=None) -> POS:
        """
        PUBLIC!
        RETURN: clipped position within world bounds
        USAGE: use this to ensure positions are within valid world limits
        """
        x, y, z = pos
        cx = min(max(x, ROW.XMIN), ROW.XMAX - 1)
        cy = min(max(y, ROW.YMIN), ROW.YMAX - 1)
        cz = min(max(z, ROW.ZMIN), ROW.ZMAX - 1)
        pos: POS = (cx, cy, cz)
        return pos
    
    @staticmethod
    def SORT(p0:POS=None, p1:POS=None) -> tuple[POS, POS]:
        """
        PUBLIC!
        RETURN: sorted positions (p0, p1) with p0 <= p1 for each coordinate
        """
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        sx0, sx1 = (min(x0, x1), max(x0, x1))
        sy0, sy1 = (min(y0, y1), max(y0, y1))
        sz0, sz1 = (min(z0, z1), max(z0, z1))
        p0: POS = (sx0, sy0, sz0)
        p1: POS = (sx1, sy1, sz1)
        return (p0, p1)
    
    @staticmethod
    def CONTAINS(row: NDARR, pos: POS) -> bool:
        """
        PUBLIC!
        RETURN: whether the row contains the given position
        """
        x, y, z = pos
        x0, y0, z0 = ROW.P0(row=row)
        x1, y1, z1 = ROW.P1(row=row)
        return ((x0 <= x < x1) and (y0 <= y < y1) and (z0 <= z < z1))
    

    @staticmethod
    def MERGE(row0: NDARR=None, row1: NDARR=None) -> tuple[bool, bool, bool]:
        """
        PUBLIC!
        RETURN: tuple indicating if rows can be merged along each axis (x, y, z)
        """
        if row0[*ROW.IDS_MID] != row1[*ROW.IDS_MID]:
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
        """
        PUBLIC!
        RETURN: encoded flags integer
        """
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
        """
        PUBLIC!
        RETURN: tuple of flags (dirty, alive, solid, destructable, visible)
        """
        f: int = int(flags)

        dirty = (f & int(ROW.ENCODE_DIRTY)) != 0
        alive = (f & int(ROW.ENCODE_ALIVE)) != 0
        solid = (f & int(ROW.ENCODE_SOLID)) != 0
        destr = (f & int(ROW.ENCODE_DESTRUCTABLE)) != 0
        visib = (f & int(ROW.ENCODE_VISIBLE)) != 0
        return dirty, alive, solid, destr, visib


    @staticmethod
    def new(p0:POS=None, p1:POS=None, mat:str=None, rid:int=None, dirty:bool=True, alive:bool=True) -> NDARR:
        """
        PUBLIC!
        RETURN: a new ROW with given parameters
        """
        p0, p1 = ROW.SORT(p0=ROW.CLIP(pos=p0), p1=ROW.CLIP(pos=p1))
        mats: Materials = Materials()
        mat: Material = mats.mat(mat=mat)
        flags: int = ROW.ENCODE(dirty=dirty, alive=alive, solid=mat.issolid(), destructable=not mat.isindestructible(), visible=not mat.isinvisible())
        copy: NDARR = ROW.COPY()

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
        copy[*ROW.IDS_RID]    = np.uint64(rid)       # stores now the row index within material array instead of global unique id
        copy[*ROW.IDS_MID]   = np.uint64(mat.mid)  # material id
        copy[*ROW.IDS_FLAGS] = np.uint64(flags)

        if any(v < 0 for v in (copy[*ROW.IDS_DX], copy[*ROW.IDS_DY], copy[*ROW.IDS_DZ])):
            raise ValueError("p1 must be greater than or equal to p0 on all axes")
        if any(v < 0 for v in (copy[*ROW.IDS_X0], copy[*ROW.IDS_Y0], copy[*ROW.IDS_Z0])):
            raise ValueError("positions must be non-negative")
        return copy
    
    