from utils import *
from world import *
from bundle import *





def test2() -> None:
    """
    test2:
    Random single-point splits into AIR inside the default big STONE row.
    Verifies:
    - world volume invariant
    - each split point becomes AIR
    - merge() does not break invariants
    """
    rows = ROWS()
    v0 = rows.volume()
    print("WORLD VOLUME BEFORE:", v0)

    points: list[POS] = []
    for i in range(10):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=64000)
        pos = (x, y, z)
        points.append(pos)
        rows.split(pos=pos, mat="AIR")
        print(f" - SPLIT test {i+1}/10 passed.")

    v1 = rows.volume()
    print("WORLD VOLUME AFTER:", v1)
    assert v1 == v0, f"volume changed after splits: before={v0}, after={v1}"

    for pos in points:
        mat, rid, row = rows.search(pos=pos)
        assert mat == "AIR", f"expected AIR at {pos}, got {mat}"

    timer.print(msg="STARTING STEP : Now testing MERGE functionality...")
    rows.merge()
    timer.print(msg=" - MERGE completed in")

    v2 = rows.volume()
    print("WORLD VOLUME AFTER MERGE:", v2)
    assert v2 == v0, f"volume changed after merge: before={v0}, after={v2}"

    for pos in points:
        mat, rid, row = rows.search(pos=pos)
        assert mat == "AIR", f"expected AIR at {pos} after merge, got {mat}"

    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.MID2name[i])
        print(f"Material {Materials.MID2name[i]} has {n} rows after MERGE tests.")

