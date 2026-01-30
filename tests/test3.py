from utils import *
from world import *
from bundle import *




def test3() -> None:
    """
    test3:
    Create multiple 5x5x5 "mines" (AIR blocks) at random places and run merge attempts.
    Verifies:
    - world volume invariant
    - all mine points remain AIR
    """
    rows = ROWS()
    v0 = rows.volume()

    mines: list[POS] = []
    for _ in range(10):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=64000)
        mines.append((x, y, z))
    print(len(mines), "mines to be created at random positions.")

    mine_points: list[POS] = []
    for mine in mines:
        for dx in range(5):
            for dy in range(5):
                for dz in range(5):
                    pos = (mine[0] + dx, mine[1] + dy, mine[2] + dz)
                    mine_points.append(pos)
                    rows.split(pos=pos, mat="AIR")

    # merge attempts (like your original intent)
    rowsbefore = rows.nrows(mat="AIR")
    for i in range(10):
        print("Performing MERGE to consolidate AIR rows... AIR rows before:", rows.nrows(mat="AIR"), "in merge iteration:", i + 1)
        rows.merge()
        rowsafter = rows.nrows(mat="AIR")
        if rowsafter == rowsbefore:
            print(" No more AIR rows could be consolidated. Stopping MERGE.")
            break
        rowsbefore = rowsafter

    v1 = rows.volume()
    assert v1 == v0, f"volume changed: before={v0}, after={v1}"

    # verify all mine points still AIR
    for pos in random.sample(mine_points, k=min(2000, len(mine_points))):
        mat, rid, row = rows.search(pos=pos)
        assert mat == "AIR", f"expected AIR at {pos}, got {mat}"

    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after MERGE tests.")
        if Materials.idx2name[i] == "AIR":
            for j in range(n):
                row = rows.array[i][j]
                print(f"  AIR row {j}: p0={ROW.P0(row=row)}, p1={ROW.P1(row=row)}")

    print(f"air rows= {rows.nrows(mat='AIR')}", f"stone rows= {rows.nrows(mat='STONE')}")

