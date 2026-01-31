from world.buildings.miner import Miner
import random
from world import ROWS


def test8() -> None:
    miners = []
    rows = ROWS()
    for i in range(60):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=60000)
        miner = Miner(rows=rows, pos=(x, y, z), size=(10, 10, 10), seconds=1)
        miners.append(miner)
    print(f"Created {len(miners)} miners.")

    # Simulate updates for 120 frames (~2 seconds)
    for frame in range(300):
        for miner in miners:
            miner: Miner = miner
            miner.update(frame=frame)