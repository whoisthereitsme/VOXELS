# tests/test5.py

from utils import *
from world import *
from bundle import *


def test5() -> None:
    """
    test5:
    Split off regions that span multiple rows (overlapping allowed).
    Verifies:
    - world volume invariant
    - AIR volume computed via rows.volume(mat="AIR")
    - random points inside carved regions are AIR
    """
    rows = ROWS()

    # remove default huge STONE row
    rows.remove(row=rows.get(mat="STONE", rid=0))

    cell = 64
    nx = 20
    ny = 20
    nz = 8

    for ix in range(nx):
        x0 = ix * cell
        x1 = x0 + cell
        for iy in range(ny):
            y0 = iy * cell
            y1 = y0 + cell
            for iz in range(nz):
                z0 = iz * cell
                z1 = z0 + cell
                rows.insert(p0=(x0, y0, z0), p1=(x1, y1, z1), mat="STONE")

    rows.merge()

    max_x = nx * cell
    max_y = ny * cell
    max_z = nz * cell

    v0 = rows.volume()
    print("WORLD VOLUME BEFORE:", v0)
    print("Initial rows:", f"stone_rows={rows.nrows(mat='STONE')}", f"air_rows={rows.nrows(mat='AIR')}")

    carved_boxes: list[tuple[POS, POS]] = []

    for i in range(30):
        dx = random.randint(cell + 5, cell * 3)
        dy = random.randint(cell + 5, cell * 3)
        dz = random.randint(cell + 5, cell * 2)

        ox = random.randint(1, cell - 2)
        oy = random.randint(1, cell - 2)
        oz = random.randint(1, cell - 2)

        x0_base = random.randint(0, max_x - dx - ox)
        y0_base = random.randint(0, max_y - dy - oy)
        z0_base = random.randint(0, max_z - dz - oz)

        x0 = x0_base + ox
        y0 = y0_base + oy
        z0 = z0_base + oz

        x1 = min(x0 + dx, max_x)
        y1 = min(y0 + dy, max_y)
        z1 = min(z0 + dz, max_z)

        p0, p1 = ROW.SORT(p0=(x0, y0, z0), p1=(x1, y1, z1))
        if p0[0] >= p1[0] or p0[1] >= p1[1] or p0[2] >= p1[2]:
            continue

        rows.split(pos=p0, pos1=p1, mat="AIR")
        carved_boxes.append((p0, p1))

        if (i + 1) % 10 == 0:
            print(f" - carved {i+1}/30 boxes")

    rows.merge()

    v1 = rows.volume()
    print("WORLD VOLUME AFTER:", v1)
    assert v1 == v0, f"world volume changed: before={v0}, after={v1}"

    air_vol = rows.volume(mat="AIR")
    print("AIR VOLUME:", air_vol)

    for _ in range(1000):
        p0, p1 = random.choice(carved_boxes)
        x = random.randint(p0[0], p1[0] - 1)
        y = random.randint(p0[1], p1[1] - 1)
        z = random.randint(p0[2], p1[2] - 1)
        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat == "AIR", f"expected AIR at {(x,y,z)}, got {mat}"

    print("test5 OK:", f"air_rows={rows.nrows(mat='AIR')}", f"stone_rows={rows.nrows(mat='STONE')}")
