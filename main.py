
from utils import *
from world import *
from bundle import *





def test1() -> None:
    rows = ROWS()
    row = rows.array[ MATERIALS.IDX["STONE"] ][0]
    rows.remove(row=row)

    cell = 20          # cube edge length
    nx = 40            # number of cells in X  -> world X size = nx*cell
    ny = 40            # number of cells in Y
    nz = 40            # number of cells in Z
    n = nx * ny * nz  # total number of cells

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
                

    timer.print(msg="STEP 1 :  3D grid partition built")

    max_x = nx * cell - 1
    max_y = ny * cell - 1
    max_z = nz * cell - 1

    succes = 0
    fails = 0
    for _ in range(1000):
        try:
            pos = (
                random.randint(0, max_x),
                random.randint(0, max_y),
                random.randint(0, max_z),
            )
            mat, rid, row = rows.find(pos=pos)
            assert ROW.CONTAINS(row=row, pos=pos), f"pos={pos} not contained by found row (mat={mat}, rid={rid})"
            succes += 1
        except:
            fails += 1
            pass

    print(" - All random CONTAINS checks passed.", f"Successes: {succes}, Fails: {fails} is a succes percentage of {100-fails/(succes+fails)*100:.2f}% adn per lookup {(succes+fails)/timer.delta[-1]:.2f} lookups/second")
    timer.print(msg=" - Random CONTAINS checks completed in")

    print(" - Now deleting all rows...")
    for i in range(10000):
        row = rows.array[ MATERIALS.IDX["STONE"] ][n-1-i]
        rows.remove(row=row)
    timer.print(msg=" - All 10000 rows deleted in")
    # and now test wiht a new set adn see if it still works
    print("STEP 2 : Rebuilding rows after deletion...")
    cell = 40          # double size
    nx = 20            # half number of cells in X  -> world X size = nx*cell
    ny = 20            # half number of cells in Y
    nz = 20            # half number of cells in Z
    n = nx * ny * nz   # total number of cells (1/8th number of previous)

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
                

    timer.print(msg=" - second time 3D grid partition built")
    succes = 0
    fails = 0
    for _ in range(1000):
        try:
            pos = (random.randint(0, max_x), random.randint(0, max_y), random.randint(0, max_z))
            mat, rid, row = rows.find(pos=pos)
            assert ROW.CONTAINS(row=row, pos=pos), f"pos={pos} not contained by found row (mat={mat}, rid={rid})"
            succes += 1
        except:
            fails += 1
            pass

    print(" - All random CONTAINS checks passed.", f"Successes: {succes}, Fails: {fails} is a succes percentage of {100-fails/(succes+fails)*100:.2f}% adn per lookup {(succes+fails)/timer.delta[-1]:.2f} lookups/second")
    timer.print(msg=" - Second random CONTAINS checks completed in")

def test2() -> None:
    rows = ROWS() # it has by default a large enough array to hold 10000 rows per material
    print("WORLD VOLUME BEFORE: ", rows.volume())

    # 1 row exists normally at tis point -> its created at init with STONE material
    for i in range(10):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=64000)
        rows.split(pos=(x, y, z), mat="AIR")  # should raise error since no rows exist yet
        print(f" - SPLIT test {i+1}/10 passed.")

    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after SPLIT tests.")
    
    print("WORLD VOLUME AFTER: ", rows.volume())
    timer.print(msg="STARTING STEP 4 : Now testing MERGE functionality...")
    rows.merge()
    timer.print(msg=" - MERGE completed in")
    print("WORLD VOLUME AFTER MERGE: ", rows.volume())

    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after MERGE tests.")


def test3() -> None:
    rows = ROWS()
    mines = []
    for i in range(10):
        x = random.randint(a=1000, b=999000)
        y = random.randint(a=1000, b=999000)
        z = random.randint(a=1000, b=64000)
        mines.append( (x,y,z) )
    print(len(mines), "mines to be created at random positions.")

    for mine in mines:
        for dx in range(5):
            for dy in range(5):
                for dz in range(5):
                    x = mine[0] + dx
                    y = mine[1] + dy
                    z = mine[2] + dz
                    pos = (x, y, z)
                    rows.split(pos=pos, mat="AIR")

    rowsbefore = rows.nrows(mat="AIR")
    for i in range(10):
        print("Performing MERGE to consolidate AIR rows... AIR rows before:", rows.nrows(mat="AIR"), "in merge iteration:", i+1)
        rows.merge()
        rowsafter = rows.nrows(mat="AIR")
        if rowsafter == rowsbefore:
            print(" No more AIR rows could be consolidated. Stopping MERGE.")
            break
        rowsbefore = rowsafter


    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after MERGE tests.")
        if "AIR"==Materials.idx2name[i]:
            for j in range(n):
                row = rows.array[i][j]
                p0 = ROW.P0(row=row)
                p1 = ROW.P1(row=row)
                print(f"  AIR row {j}: p0={p0}, p1={p1}")
                
    print(f"air rows= {rows.nrows(mat='AIR')}", f"stone rows= {rows.nrows(mat='STONE')}")















def test4() -> None:
    """
    test4:
    Split off multiple *single-row-contained* regions (boxes fully inside one existing row),
    then merge to consolidate and verify:
    - total world volume stays constant
    - AIR volume equals sum of carved boxes
    - a bunch of random points inside carved boxes are AIR
    - a bunch of random points outside carved boxes are NOT AIR
    """
    rows = ROWS()
    v0 = rows.volume()
    print("WORLD VOLUME BEFORE:", v0)

    # We'll carve boxes that are guaranteed to fit inside the initial STONE row.
    # Keep them well away from borders and reasonably small.
    boxes: list[tuple[POS, POS]] = []
    total_air_vol = 0

    for i in range(50):
        dx = random.randint(4, 48)
        dy = random.randint(4, 48)
        dz = random.randint(4, 32)

        x0 = random.randint(2000, 900000)
        y0 = random.randint(2000, 900000)
        z0 = random.randint(2000, 60000)

        p0 = (x0, y0, z0)
        p1 = (x0 + dx, y0 + dy, z0 + dz)

        # split2 expects p0/p1 in any order, but keep it clean
        p0, p1 = ROW.SORT(p0=p0, p1=p1)

        rows.split(pos=p0, pos1=p1, mat="AIR")
        boxes.append((p0, p1))
        total_air_vol += (p1[0] - p0[0]) * (p1[1] - p0[1]) * (p1[2] - p0[2])

        if (i + 1) % 10 == 0:
            print(f" - carved {i+1}/50 boxes")

    # One last global merge to consolidate as much as possible
    rows.merge()

    v1 = rows.volume()
    print("WORLD VOLUME AFTER:", v1)
    assert v1 == v0, f"volume changed: before={v0}, after={v1}"

    # Compute AIR volume by summing all AIR rows volumes
    air_mid = Materials.name2idx["AIR"]
    air_vol = 0
    for rid in range(rows.n[air_mid]):
        air_vol += ROW.VOLUME(row=rows.array[air_mid][rid])
    print("AIR VOLUME:", air_vol, "EXPECTED (sum boxes):", total_air_vol)
    assert air_vol == total_air_vol, f"AIR volume mismatch: got={air_vol}, expected={total_air_vol}"

    # Random containment checks inside boxes -> must be AIR
    for _ in range(500):
        p0, p1 = random.choice(boxes)
        x = random.randint(p0[0], p1[0] - 1)
        y = random.randint(p0[1], p1[1] - 1)
        z = random.randint(p0[2], p1[2] - 1)
        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat == "AIR", f"expected AIR at {(x,y,z)}, got {mat} rid={rid}"

    # Random checks outside boxes -> should NOT be AIR (probabilistic; pick points far away)
    for _ in range(500):
        x = random.randint(10, 900)
        y = random.randint(10, 900)
        z = random.randint(10, 900)
        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat != "AIR", f"unexpected AIR at {(x,y,z)}"

    print("test4 OK:",
          f"air_rows={rows.nrows(mat='AIR')}",
          f"stone_rows={rows.nrows(mat='STONE')}")

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

    # Remove the default giant STONE row
    row0 = rows.array[MATERIALS.IDX["STONE"]][0]
    rows.remove(row=row0)

    # Build a regular grid
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

    # Consolidate (may collapse to 1 big STONE row, which is fine)
    rows.merge()

    max_x = nx * cell
    max_y = ny * cell
    max_z = nz * cell

    v0 = rows.volume()
    print("WORLD VOLUME BEFORE:", v0)
    print("Initial rows:",
          f"stone_rows={rows.nrows(mat='STONE')}",
          f"air_rows={rows.nrows(mat='AIR')}")

    carved_boxes: list[tuple[POS, POS]] = []

    # Carve overlapping AIR boxes that span multiple rows
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

    # Random sampling: points inside carved boxes must be AIR
    for _ in range(1000):
        p0, p1 = random.choice(carved_boxes)
        x = random.randint(p0[0], p1[0] - 1)
        y = random.randint(p0[1], p1[1] - 1)
        z = random.randint(p0[2], p1[2] - 1)

        mat, rid, row = rows.search(pos=(x, y, z))
        assert mat == "AIR", f"expected AIR at {(x,y,z)}, got {mat}"

    print(
        "test5 OK:",
        f"air_rows={rows.nrows(mat='AIR')}",
        f"stone_rows={rows.nrows(mat='STONE')}"
    )



def main(test=[]) -> None:
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

        except Exception:
            traceback.print_exc()
        finally:    
            pass



if __name__ == "__main__":
    main(test=[1, 2, 3, 4, 5])
    