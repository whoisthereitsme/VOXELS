from utils import *
from world import *
from bundle import *


def test1() -> None:
    """
    test1:
    Build a dense 3D grid of STONE AABBs, then verify BVH partition integrity by:
    - random point lookups must always find a row
    - found row must CONTAIN the queried point
    Then delete a chunk of rows, rebuild a different grid, and re-run the same checks.
    """
    rows = ROWS()

    # remove the default huge row
    row0 = rows.array[MATERIALS.IDX["STONE"]][0]
    rows.remove(row=row0)

    # STEP 1 grid
    cell = 20
    nx = 40
    ny = 40
    nz = 40
    n = nx * ny * nz

    timer.lap()
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
    timer.print(msg="STEP 1 : 3D grid partition built")

    max_x = nx * cell - 1
    max_y = ny * cell - 1
    max_z = nz * cell - 1

    succes = 0
    fails = 0
    for _ in range(1000):
        pos = (
            random.randint(0, max_x),
            random.randint(0, max_y),
            random.randint(0, max_z),
        )
        try:
            mat, rid, row = rows.search(pos=pos)
            assert ROW.CONTAINS(row=row, pos=pos), f"pos={pos} not contained (mat={mat}, rid={rid}) p0={ROW.P0(row=row)} p1={ROW.P1(row=row)}"
            succes += 1
        except Exception:
            fails += 1
            raise

    assert fails == 0, f"BVH/grid lookup failures in STEP 1: {fails} (success={succes})"
    print(f" - STEP 1 lookup checks OK: {succes} successes, {fails} fails, {succes/timer.delta[-1]:.2f} lookups/sec")
    timer.print(msg=" - STEP 1 lookups completed in")

    # delete some rows (stress BVH remove/swap)
    print(" - Now deleting 10000 rows...")
    for i in range(10000):
        row = rows.array[MATERIALS.IDX["STONE"]][rows.nrows(mat="STONE") - 1]
        rows.remove(row=row)
    timer.print(msg=" - Deleted 10000 rows in")

    # STEP 2 grid (new scale) — rebuild from scratch for clean bounds
    # delete remaining STONE rows
    while rows.nrows(mat="STONE") > 0:
        row = rows.array[MATERIALS.IDX["STONE"]][rows.nrows(mat="STONE") - 1]
        rows.remove(row=row)

    print("STEP 2 : Rebuilding rows after deletion...")
    cell = 40
    nx = 20
    ny = 20
    nz = 20
    n2 = nx * ny * nz

    timer.lap()
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
    timer.print(msg=" - STEP 2 grid partition built")

    max_x = nx * cell - 1
    max_y = ny * cell - 1
    max_z = nz * cell - 1

    succes = 0
    fails = 0
    for _ in range(1000):
        pos = (
            random.randint(0, max_x),
            random.randint(0, max_y),
            random.randint(0, max_z),
        )
        mat, rid, row = rows.search(pos=pos)
        assert ROW.CONTAINS(row=row, pos=pos), f"pos={pos} not contained (mat={mat}, rid={rid}) p0={ROW.P0(row=row)} p1={ROW.P1(row=row)}"
        succes += 1

    assert fails == 0, f"BVH/grid lookup failures in STEP 2: {fails} (success={succes})"
    print(f" - STEP 2 lookup checks OK: {succes} successes, {fails} fails, {succes/timer.delta[-1]:.2f} lookups/sec")
    timer.print(msg=" - STEP 2 lookups completed in")


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
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after MERGE tests.")


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

    row0 = rows.array[MATERIALS.IDX["STONE"]][0]
    rows.remove(row=row0)

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








def test6() -> None:
    """
    test6:
    Timing benchmark for core operations.

    Measures (10x each):
    - bulk insert (grid build)
    - random BVH search
    - split1 (single-point split)
    - split2 (region split spanning rows)
    - merge
    - remove
    """

    print("=== TEST6: TIMING BENCHMARK ===")

    # -----------------------------
    # 1) BULK INSERT (grid build)
    # -----------------------------
    timer.lap()
    for _ in range(10):
        rows = ROWS()
        row0 = rows.array[MATERIALS.IDX["STONE"]][0]
        rows.remove(row=row0)

        cell = 32
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
    timer.print(msg="test6: bulk insert (grid build) x10")

    # -----------------------------
    # 2) RANDOM SEARCH (BVH)
    # -----------------------------
    timer.lap()
    max_x = nx * cell - 1
    max_y = ny * cell - 1
    max_z = nz * cell - 1

    for _ in range(10):
        pos = (
            random.randint(0, max_x),
            random.randint(0, max_y),
            random.randint(0, max_z),
        )
        rows.search(pos=pos)
    timer.print(msg="test6: BVH search (1000 lookups ×10)")

    # -----------------------------
    # 3) SPLIT1 (single-point)
    # -----------------------------
    timer.lap()
    for _ in range(10):
        pos = (
            random.randint(10, max_x - 10),
            random.randint(10, max_y - 10),
            random.randint(10, max_z - 10),
        )
        rows.split(pos=pos, mat="AIR")
    timer.print(msg="test6: split1 (single-point)")

    # -----------------------------
    # 4) SPLIT2 (region / box)
    # -----------------------------
    timer.lap()
    for _ in range(10):
            dx = random.randint(cell, cell * 3)
            dy = random.randint(cell, cell * 3)
            dz = random.randint(cell, cell * 2)

            x0 = random.randint(0, max_x - dx)
            y0 = random.randint(0, max_y - dy)
            z0 = random.randint(0, max_z - dz)

            p0, p1 = ROW.SORT(
                p0=(x0, y0, z0),
                p1=(x0 + dx, y0 + dy, z0 + dz),
            )
            rows.split(pos=p0, pos1=p1, mat="AIR")
    timer.print(msg="test6: split2 (region split)")

    # -----------------------------
    # 5) MERGE
    # -----------------------------
    timer.lap()
    for _ in range(10):
        rows.merge()
    timer.print(msg="test6: merge()")

    # -----------------------------
    # 6) REMOVE (random rows)
    # -----------------------------
    timer.lap()
    for _ in range(10):
        mid = MATERIALS.IDX["STONE"]
        n = rows.nrows(mat="STONE")
        remove_count = min(500, n)
        for i in range(remove_count):
            row = rows.array[mid][n - 1 - i]
            rows.remove(row=row)
    timer.print(msg="test6: remove()")

    print("=== TEST6 DONE ===")









def main(test: list[int] = None) -> None:
    if test is None:
        test = [1, 2, 3, 4, 5, 6]

    timer.lap()
    with Bundle():
        try:
            if 1 in test:
                test1()
            if 2 in test:
                test2()
            if 3 in test:
                test3()
            if 4 in test:
                test4()
            if 5 in test:
                test5()
            if 6 in test:
                test6()

        except Exception:
            traceback.print_exc()
        finally:
            pass


if __name__ == "__main__":
    timer.lap()
    main(test=[6])
    