# tests/test7.py

from utils import *
from world import *


def test7() -> None:
    """
    test7:
    Bulletproof Resource/Resources/Warehouse invariants.
    """
    print("=== TEST7: RESOURCE / WAREHOUSE INVARIANTS ===")

    # 1) Resource.split() invariants
    for _ in range(1000):
        amount = random.randint(0, 10_000)
        value = random.randint(0, 12_000)

        r = Resource(mat="STONE", amount=amount)
        original = r.copy()

        part1, leftover = r.split(value=value)  # [taken, leftover]

        assert part1.mat == original.mat
        assert leftover.mat == original.mat

        assert 0 <= part1.amount <= original.amount
        assert 0 <= leftover.amount <= original.amount

        assert part1.amount == min(value, original.amount)
        assert part1.amount + leftover.amount == original.amount

    print(" - split() invariants OK (1000 cases)")

    # 2) Resource arithmetic semantics (mutating)
    a = Resource(mat="STONE", amount=50)
    b = Resource(mat="STONE", amount=20)

    a0 = a.amount
    b0 = b.amount
    a + b
    assert a.amount == a0 + b0
    assert b.amount == b0

    a = Resource(mat="STONE", amount=50)
    b = Resource(mat="STONE", amount=20)
    a += b
    assert a.amount == 70
    assert b.amount == 0

    a = Resource(mat="STONE", amount=50)
    b = Resource(mat="STONE", amount=20)
    a0 = a.amount
    b0 = b.amount
    a - b
    assert a.amount == a0 - b0
    assert b.amount == b0

    a = Resource(mat="STONE", amount=10)
    b = Resource(mat="STONE", amount=20)
    a0 = a.amount
    b0 = b.amount
    a - b
    assert a.amount == 0
    assert b.amount == b0

    a = Resource(mat="STONE", amount=10)
    b = Resource(mat="STONE", amount=20)
    a -= b
    assert a.amount == 0
    assert b.amount == 10

    print(" - Resource +/- semantics OK")

    # 3) Resources ingest/transfer semantics
    inv = Resources(rez=[])
    r1 = Resource(mat="STONE", amount=10)
    r2 = Resource(mat="STONE", amount=5)

    inv + r1
    assert inv.get(mat="STONE").amount == 10
    assert r1.amount == 10

    inv += r2
    assert inv.get(mat="STONE").amount == 15
    assert r2.amount == 0

    print(" - Resources ingest/transfer OK")

    # 4) Warehouse.give()/take() invariants
    wh = Warehouse(rows=None, pos=(0, 0, 0), size=(2, 2, 2))  # cap = 512
    assert wh.cap == 512
    assert wh.total() == 0
    assert wh.free() == 512

    incoming = Resource(mat="STONE", amount=600)
    leftover = wh.give(incoming=incoming)

    assert wh.get(mat="STONE").amount == 512
    assert leftover.mat == "STONE"
    assert leftover.amount == 88

    req = Resource(mat="STONE", amount=200)
    taken = wh.take(requested=req)

    assert taken.mat == "STONE"
    assert taken.amount == 200
    assert wh.get(mat="STONE").amount == 312

    req2 = Resource(mat="STONE", amount=9999)
    taken2 = wh.take(requested=req2)

    assert taken2.amount == 312
    assert wh.get(mat="STONE").amount == 0

    print(" - Warehouse give/take invariants OK")
    print("=== TEST7 DONE ===")
