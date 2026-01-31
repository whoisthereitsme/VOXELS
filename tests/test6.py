from utils import *
from world import *
from bundle import *




def test6() -> None:
    """
    test6:
    Timing benchmark: 100 calls per operation category.
    IMPORTANT: each category runs on a fresh baseline world so timings stay comparable.
    """
    print("=== TEST6: TIMING BENCHMARK (100 calls per op, fresh world per op) ===")
    ntests = 10

    def make_world() -> tuple[ROWS, int, int, int, int]:
        rows = ROWS()
        row0 = rows.array[MATERIALS.MID["STONE"]][0]
        rows.remove(row=row0)

        cell = 64
        nx, ny, nz = 20, 20, 8
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    x0 = ix * cell
                    y0 = iy * cell
                    z0 = iz * cell
                    rows.insert(
                        p0=(x0, y0, z0),
                        p1=(x0 + cell, y0 + cell, z0 + cell),
                        mat="STONE",
                    )

        rows.merge()
        max_x = nx * cell - 1
        max_y = ny * cell - 1
        max_z = nz * cell - 1
        return rows, cell, max_x, max_y, max_z

    # 1) SEARCH
    rows, cell, max_x, max_y, max_z = make_world()
    timer.lap()
    for _ in range(ntests):
        pos = (random.randint(0, max_x), random.randint(0, max_y), random.randint(0, max_z))
        rows.search(pos=pos)
    timer.print(msg=f"test6: search() [tests={ntests}]")

    # 2) SPLIT1
    rows, cell, max_x, max_y, max_z = make_world()
    timer.lap()
    for _ in range(ntests):
        pos = (random.randint(10, max_x - 10), random.randint(10, max_y - 10), random.randint(10, max_z - 10))
        rows.split(pos=pos, mat="AIR")
    timer.print(msg=f"test6: split1 (point split) [tests={ntests}]")

    # 3) SPLIT2
    rows, cell, max_x, max_y, max_z = make_world()
    timer.lap()
    for _ in range(ntests):
        dx = random.randint(cell + 5, cell * 3)
        dy = random.randint(cell + 5, cell * 3)
        dz = random.randint(cell + 5, cell * 2)

        x0 = random.randint(0, max_x - dx)
        y0 = random.randint(0, max_y - dy)
        z0 = random.randint(0, max_z - dz)

        p0, p1 = ROW.SORT(p0=(x0, y0, z0), p1=(x0 + dx, y0 + dy, z0 + dz))
        rows.split(pos=p0, pos1=p1, mat="AIR")
    timer.print(msg=f"test6: split2 (region split) [tests={ntests}]")

    # 4) MERGE (meaningful merge: first fragment it a bit)
    rows, cell, max_x, max_y, max_z = make_world()
    for _ in range(200):
        pos = (random.randint(10, max_x - 10), random.randint(10, max_y - 10), random.randint(10, max_z - 10))
        rows.split(pos=pos, mat="AIR")
    timer.lap()
    for _ in range(ntests):
        rows.merge()
    timer.print(msg=f"test6: merge() [tests={ntests}]")

    # 5) REMOVE (remove from STONE preferentially)
    rows, cell, max_x, max_y, max_z = make_world()
    timer.lap()
    for _ in range(ntests):
        if rows.nrows(mat="STONE") <= 0:
            break
        row = rows.array[MATERIALS.MID["STONE"]][rows.nrows(mat="STONE") - 1]
        rows.remove(row=row)
    timer.print(msg=f"test6: remove() [tests={ntests}]")

    # 6) INSERT (small inserts)
    rows, cell, max_x, max_y, max_z = make_world()
    timer.lap()
    for _ in range(ntests):
        x0 = random.randint(0, max_x - 2)
        y0 = random.randint(0, max_y - 2)
        z0 = random.randint(0, max_z - 2)
        rows.insert(p0=(x0, y0, z0), p1=(x0 + 1, y0 + 1, z0 + 1), mat="STONE")
    timer.print(msg=f"test6: insert() [tests={ntests}]")

    print("=== TEST6 DONE ===")


