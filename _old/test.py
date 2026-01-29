# test_sim.py
from __future__ import annotations

import random
import time

from .boxes import Boxes
from .mine import Mine
from .config import Config


def test() -> dict[int, dict[str, float]]:
    wx, wy, wz = Config.XMAX-1, Config.YMAX-1, Config.ZMAX-1
    padding = int(Config.SIDEPAD)
    mineout = (int(Config.MINEX), int(Config.MINEY), int(Config.MINEZ))
    nframes = int(Config.FPS_TGT)

    boxes = Boxes(size=(wx, wy, wz))
    mined: set[tuple[int, int, int]] = set()

    mines: dict[int, list[Mine]] = {i: [] for i in range(nframes)}
    Mine.mineidx = 0
    iteration = 0
    currentframe = 0
    perc1 = 0.0
    nmined = 0

    while True:
        
        iteration += 1
        x = random.randint(padding, wx - padding - 1)
        y = random.randint(padding, wy - padding - 1)
        z = wz - mineout[2]
        sx = 50 
        sy = 50
        sz = 50
        m = Mine(x=x, y=y, z=z, sx=sx, sy=sy, sz=sz)
        mines[m.nextframe].append(m)
        mat1 = Config.MATERIALS["STONE"]
        mat0 = Config.MATERIALS["AIR"]
        t0 = time.time()
        totalnmines = sum(len(mlist) for mlist in mines.values())
        print(f"Iteration {iteration}: total mines={totalnmines}; starting mining step...")
        nsplit0 = len(boxes.array[mat0]) + len(boxes.array[mat1])
        for m in mines[currentframe]:
            pos = m.next(frame=currentframe)
            if pos is not None and pos not in mined:
                mined.add(pos)
                nmined += 1
                boxes.split(pos=pos, mat=mat0)
        nsplit1 = len(boxes.array[mat0]) + len(boxes.array[mat1])
        nsplit = nsplit1 - nsplit0

        nmerge0 = (len(boxes.array[mat0]) + len(boxes.array[mat1]))
        t1 = time.time()
        t2 = time.time()
        if iteration % 6 == 3:
            boxes.merge(rows=boxes.array[mat1], mat=mat1)
        if iteration % 6 == 0:
            boxes.merge(rows=boxes.array[mat0], mat=mat0)
        t4 = time.time()
        dt01 = t1 - t0
        dt24 = t4 - t2
        nmerge1 = (len(boxes.array[mat0]) + len(boxes.array[mat1]))
        nmerge = nmerge0 - nmerge1
        nadded = nsplit - nmerge
        print(f"Iteration {iteration}: mined {nmined} boxes; dt01={dt01:.4f}s dt24={dt24:.4f}s nsplit={nsplit}, nmerge={nmerge}, nadded={nadded}, total boxes={nmerge1}")

if __name__ == "__main__":
    test()