from world.buildings.miner import Miner
import random
from world import ROWS
import time

def test8() -> None:
    miners = []
    rows = ROWS()
    for i in range(300):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=9000)
        miner = Miner(rows=rows, pos=(x, y, z), size=(20, 20, 50000), seconds=1, floor=True)

        miners.append(miner)
    print(f"Created {len(miners)} miners.")

    duration = 1200  # seconds
    print(f"Simulating {duration} seconds of mining...")
    t0 = time.time()
    for frame in range(duration * 60):
        for miner in miners:
            miner: Miner = miner
            miner.update(frame=frame)
        if (frame + 1) % 60 == 0:
            print(f"  Simulated {(frame + 1) // 60} seconds...")
    t1 = time.time()
    dt = t1 - t0
    remaining = duration - dt
    print(f"Simulated {duration} seconds in {dt:.2f} seconds. Remaining time: {remaining:.2f} seconds.")

    print(rows)
