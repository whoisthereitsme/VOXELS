from __future__ import annotations
import random
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from world.rows import ROWS


from utils.types import POS, SIZE









class Miner:
    id = 0
    def __init__(self, rows:ROWS=None, pos:POS=None, size:SIZE=None, seconds:int=1, floor:bool=True) -> None:
        self.rows:ROWS      = rows
        self.pos:POS        = pos
        self.size:SIZE      = size
        self.seconds:int    = seconds
        self.floor:bool     = floor
        print(f"Creating Miner id={Miner.id} at pos={self.pos} size={self.size} seconds={self.seconds} floor={self.floor}")

        self.init()

    def init(self) -> None:
        self.id:int         = self.getid()
        self.nframes:int    = self.seconds * 60 if not self.floor else self.seconds * 60 * (self.size[0] * self.size[1]) + random.randint(0, 59) # to spread out floor miners
        self.frame:int      = self.getframe()

        self.minepos0:POS    = self.pos
        self.minepos1:POS    = (self.pos[0]+self.size[0]-1, self.pos[1]+self.size[1]-1, self.pos[2]+self.size[2]-1)
        self.minepos:POS     = self.minepos0

    def getid(self) -> int:
        id: int = Miner.id
        Miner.id += 1
        return id
    
    def getframe(self) -> int:
        frame:int = self.id % self.nframes
        return frame
    
    def getnext(self) -> tuple[POS, POS]:
        x0, y0, z0 = self.minepos0
        x1, y1, z1 = self.minepos1
        x, y, z = self.minepos

        pos:POS = (x, y, z) # will be returned to be mined
        if self.floor==False:
            x += 1
            if x > x1: 
                x, y = x0, y + 1
                if y > y1: 
                    y, z = y0, z + 1
                    if z > z1: 
                        z = z0

            self.minepos = (x, y, z)    # update to next position
            pos1 = (pos[0] + 1, pos[1] + 1, pos[2] + 1)
            return pos, pos1
        else:
            boxpos0:POS = (x0, y0, z)
            boxpos1:POS = (x1, y1, z + 1)

            z += 1
            if z > z1:
                z = z0

            self.minepos = (x, y, z)    # update to next position
            return (boxpos0, boxpos1)
    
    def update(self, frame:int) -> None:
        self.mine(frame=frame)
    
    def mine(self, frame:int=None) -> None:
        if frame is None:
            raise ValueError("frame must be specified")
        if frame % self.nframes == self.frame:  # every nframes frames
            pos0, pos1 = self.getnext()
            self.rows.split(pos=pos0, pos1=pos1, mat="AIR")
        else:
            pass

    
