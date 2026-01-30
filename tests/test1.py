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

