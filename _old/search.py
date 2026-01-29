from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional
if TYPE_CHECKING:
    from .boxes import Boxes

from bisect import bisect_left, bisect_right
from .config import Config, POS, np


class Search:
    def __init__(self, boxes: Boxes) -> None:
        if boxes is None:
            raise ValueError("boxes must be provided")
        self.boxes = boxes

        wx, wy, wz = boxes.size
        self.xcuts: list[int] = [0, int(wx)]
        self.ycuts: list[int] = [0, int(wy)]
        self.zcuts: list[int] = [0, int(wz)]

        # owner[(ix,iy,iz)] = box_id
        self.owner: dict[tuple[int, int, int], int] = {}

        # seed if initial box exists
        stone = int(Config.MATERIALS["STONE"])
        a = boxes.array[stone]
        if a.size != 0:
            row0 = a[0].copy()
            self.register([row0])

    def find(self, pos: POS) -> int | None:
        ix, iy, iz = self.cell(pos)
        bid = self.owner.get((ix, iy, iz))
        return int(bid) if bid is not None else None

    def cell(self, pos: POS) -> tuple[int, int, int]:
        x, y, z = pos
        ix = int(bisect_right(self.xcuts, int(x)) - 1)
        iy = int(bisect_right(self.ycuts, int(y)) - 1)
        iz = int(bisect_right(self.zcuts, int(z)) - 1)
        return (ix, iy, iz)

    def handle(
        self,
        *,
        addrow: Optional[np.ndarray] = None,
        addrows: Optional[Iterable[np.ndarray]] = None,
        delrow: Optional[np.ndarray] = None,
        delrows: Optional[Iterable[np.ndarray]] = None,
    ) -> None:
        old_list: list[np.ndarray] = []
        new_list: list[np.ndarray] = []

        if delrow is not None:
            old_list.append(delrow)
        if delrows is not None:
            old_list.extend(list(delrows))

        if addrow is not None:
            new_list.append(addrow)
        if addrows is not None:
            new_list.extend(list(addrows))

        if old_list:
            self.unregister(old_list)
        if new_list:
            self.register(new_list)

    def register(self, rows: Iterable[np.ndarray]) -> None:
        rows_list = list(rows)
        if not rows_list:
            return

        # 1) ensure cuts exist (and remap owner if a new cut is inserted)
        for r in rows_list:
            self._ensure_row_cuts_and_remap(r)

        # 2) assign owners
        for r in rows_list:
            self._owner_set_row(int(r[Config.ID]), r)

    def unregister(self, rows: Iterable[np.ndarray]) -> None:
        rows_list = list(rows)
        if not rows_list:
            return

        # cuts should already exist, but keep robust:
        for r in rows_list:
            self._ensure_row_cuts_and_remap(r)

        for r in rows_list:
            self._owner_clear_row(int(r[Config.ID]), r)

    # ------------------------------------------------------------
    # Internals (kept internal, but logic is straightforward)
    # ------------------------------------------------------------

    def _ensure_row_cuts_and_remap(self, row: np.ndarray) -> None:
        if row is None or int(row.size) != 9:
            raise ValueError("row must be length-9 ndarray")

        # Insert cuts one-by-one; if any insertion happens, remap owner incrementally.
        self._ins_cut_x(int(row[Config.X0]))
        self._ins_cut_x(int(row[Config.X1]))
        self._ins_cut_y(int(row[Config.Y0]))
        self._ins_cut_y(int(row[Config.Y1]))
        self._ins_cut_z(int(row[Config.Z0]))
        self._ins_cut_z(int(row[Config.Z1]))

    def _ins_cut_x(self, v: int) -> None:
        self._ins_cut_axis(axis=0, cuts=self.xcuts, v=int(v))

    def _ins_cut_y(self, v: int) -> None:
        self._ins_cut_axis(axis=1, cuts=self.ycuts, v=int(v))

    def _ins_cut_z(self, v: int) -> None:
        self._ins_cut_axis(axis=2, cuts=self.zcuts, v=int(v))

    def _ins_cut_axis(self, axis: int, cuts: list[int], v: int) -> None:
        i = bisect_left(cuts, v)
        if i < len(cuts) and cuts[i] == v:
            return  # already exists

        # Insert new cut
        cuts.insert(i, v)

        # Remap owner indices for this axis (NO rebuild over boxes; one pass over owner dict)
        # 1) Shift indices >= i by +1
        # 2) Split the cell at index i-1: duplicate entries with index i-1 into new index i
        new_owner: dict[tuple[int, int, int], int] = {}

        if axis == 0:
            for (ix, iy, iz), bid in self.owner.items():
                if ix >= i:
                    new_owner[(ix + 1, iy, iz)] = bid
                else:
                    new_owner[(ix, iy, iz)] = bid
                if ix == i - 1:
                    new_owner[(i, iy, iz)] = bid

        elif axis == 1:
            for (ix, iy, iz), bid in self.owner.items():
                if iy >= i:
                    new_owner[(ix, iy + 1, iz)] = bid
                else:
                    new_owner[(ix, iy, iz)] = bid
                if iy == i - 1:
                    new_owner[(ix, i, iz)] = bid

        else:
            for (ix, iy, iz), bid in self.owner.items():
                if iz >= i:
                    new_owner[(ix, iy, iz + 1)] = bid
                else:
                    new_owner[(ix, iy, iz)] = bid
                if iz == i - 1:
                    new_owner[(ix, iy, i)] = bid

        self.owner = new_owner

    def _ranges_row(self, row: np.ndarray) -> tuple[range, range, range]:
        x0 = int(row[Config.X0]); x1 = int(row[Config.X1])
        y0 = int(row[Config.Y0]); y1 = int(row[Config.Y1])
        z0 = int(row[Config.Z0]); z1 = int(row[Config.Z1])

        ix0 = int(bisect_left(self.xcuts, x0))
        ix1 = int(bisect_left(self.xcuts, x1))
        iy0 = int(bisect_left(self.ycuts, y0))
        iy1 = int(bisect_left(self.ycuts, y1))
        iz0 = int(bisect_left(self.zcuts, z0))
        iz1 = int(bisect_left(self.zcuts, z1))

        return (range(ix0, ix1), range(iy0, iy1), range(iz0, iz1))

    def _owner_set_row(self, bid: int, row: np.ndarray) -> None:
        rx, ry, rz = self._ranges_row(row)
        bid = int(bid)
        for ix in rx:
            for iy in ry:
                for iz in rz:
                    self.owner[(int(ix), int(iy), int(iz))] = bid

    def _owner_clear_row(self, bid: int, row: np.ndarray) -> None:
        rx, ry, rz = self._ranges_row(row)
        bid = int(bid)
        for ix in rx:
            for iy in ry:
                for iz in rz:
                    k = (int(ix), int(iy), int(iz))
                    if self.owner.get(k) == bid:
                        del self.owner[k]
