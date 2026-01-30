from utils import *
from world import *
from bundle import *



def test4() -> None:
    """
    test4:
    Split off multiple *single-row-contained* regions (disjoint by construction) inside default big STONE row.
    Verifies:
    - world volume invariant
    - AIR volume equals sum of carved boxes (valid because we keep them disjoint)
    - random points inside carved boxes are AIR
    - random points far away are NOT AIR
    """
    rows = ROWS()
    v0 = rows.volume()
    print("WORLD VOLUME BEFORE:", v0)

    boxes: list[tuple[POS, POS]] = []
    total_air_vol = 0

    # Make boxes disjoint by placing them on a coarse lattice
    # Each "slot" is 64x64x64, and the carved box fits inside that slot.
    slot = 64
    for i in range(50):
        gx = random.randint(50, 2000) * slot
        gy = random.randint(50, 2000) * slot
        gz = random.randint(10, 900) * slot

        dx = random.randint(4, 48)
        dy = random.randint(4, 48)
        dz = random.randint(4, 32)

        x0 = gx + 1
        y0 = gy + 1
        z0 = gz + 1
        p0 = (x0, y0, z0)
        p1 = (x0 + dx, y0 + dy, z0 + dz)
        p0, p1 = ROW.SORT(p0=p0, p1=p1)

        rows.split(pos=p0, pos1=p1, mat="AIR")
        boxes.append((p0, p1))
        total_air_vol += (p1[0] - p0[0]) * (p1[1] - p0[1]) * (p1[2] - p0[2])

        if (i + 1) % 10 == 0:
            print(f" - carved {i+1}/50 boxes")

    rows.merge()

    v1 = rows.volume()
    print("WORLD VOLUME AFTER:", v1)
    assert v1 == v0, f"volume changed: before={v0}, after={v1}"

    air_vol = rows.volume(mat="AIR")
    print("AIR VOLUME:", air_vol, "EXPECTED (sum boxes):", total_air_vol)
    assert air_vol == total_air_vol, f"AIR volume mismatch: got={air_vol}, expected={total_air_vol}"

    for _ in range(500):
        p0, p1 = random.choice(boxes)
        x = random.randint(p0[0], p1[0] - 1)
        y = random.randint(p0[1], p1[1] - 1)
        z = random.randint(p0[2], p1[2] - 1)
        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat == "AIR", f"expected AIR at {(x,y,z)}, got {mat}"

    for _ in range(500):
        x = random.randint(10, 900)
        y = random.randint(10, 900)
        z = random.randint(10, 900)
        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat != "AIR", f"unexpected AIR at {(x,y,z)}"

    print("test4 OK:", f"air_rows={rows.nrows(mat='AIR')}", f"stone_rows={rows.nrows(mat='STONE')}")
