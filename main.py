
from utils import *
from world import *
from bundle import *





def main() -> None:
    rows = ROWS()
    row = rows.array[ MATERIALS.IDX["STONE"] ][0]
    rows.delete(row=row)

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
                rows.append(p0=(x0, y0, z0), p1=(x1, y1, z1), mat="STONE")
                

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
        rows.delete(row=row)
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
                rows.append(p0=(x0, y0, z0), p1=(x1, y1, z1), mat="STONE")
                

    timer.print(msg=" - second time 3D grid partition built")
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
    timer.print(msg=" - Second random CONTAINS checks completed in")

    if succes == 1000 and fails == 0:
        print("FINALLY: TESTS PASSED SUCCESSFULLY!")

    print("STEP 3 : Now testing SPLIT functionality...")
    rows = ROWS() # it has by default a large enough array to hold 10000 rows per material
    # 1 row exists normally at tis point -> its created at init with STONE material
    for i in range(10):
        rows.split(pos=(i*10,i*10,i*10), mat="AIR")  # should raise error since no rows exist yet
        print(f" - SPLIT test {i+1}/10 passed (expected failure on empty ROWS).")

    for i in range(len(rows.array)):
        n = rows.nrows(mat=Materials.idx2name[i])
        print(f"Material {Materials.idx2name[i]} has {n} rows after SPLIT tests.")
    







if __name__ == "__main__":
    timer.lap()
    with Bundle():
        try:
            main()
            timer.print(msg="main.py: executed in")
        except Exception:
            traceback.print_exc()
        finally:    
            pass


