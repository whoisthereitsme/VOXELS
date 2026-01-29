from __future__ import annotations

from .box import Box
from .config import Config, POS, np
from .search import Search


class Boxes:
    id = 0

    X0 = Config.X0
    Y0 = Config.Y0
    Z0 = Config.Z0
    X1 = Config.X1
    Y1 = Config.Y1
    Z1 = Config.Z1
    MAT = Config.MAT
    ID = Config.ID
    DIRTY = Config.DIRTY

    DIRTY_TTL = 5  # only used for split dirtiness default + optional decay clamp

    def __init__(self, size: POS) -> None:
        if size is None:
            raise ValueError("size must be provided")

        wx, wy, wz = size
        self.size = size
        self.nmats = int(len(Config.MATERIALS))

        # authoritative storage per material
        self.array: np.ndarray = np.empty((self.nmats,), dtype=object)
        for m in range(self.nmats):
            self.array[m] = np.zeros((0, 9), dtype=Config.DTYPE)

        # mapping: box_id -> (mat, idx)
        self._loc: dict[int, tuple[int, int]] = {}

        # initial world box
        stone = int(Config.MATERIALS["STONE"])
        row = np.array([0, 0, 0, wx, wy, wz, stone, self.getid(), 0], dtype=Config.DTYPE).reshape(1, 9)
        self.array[stone] = row
        self._loc[int(row[0, self.ID])] = (stone, 0)

        self.search = Search(boxes=self)

    # ============================================================
    # IDs / helpers
    # ============================================================

    def getid(self) -> int:
        i = Boxes.id
        Boxes.id += 1
        return int(i)

    def __len__(self) -> int:
        return int(sum(int(a.shape[0]) for a in self.array))

    def contains(self, pos: POS, mat: int) -> np.ndarray:
        a: np.ndarray = self.array[int(mat)]
        if a.size == 0:
            return np.zeros((0,), dtype=bool)
        px, py, pz = pos
        return (
            (a[:, self.X0] <= px) & (px < a[:, self.X1]) &
            (a[:, self.Y0] <= py) & (py < a[:, self.Y1]) &
            (a[:, self.Z0] <= pz) & (pz < a[:, self.Z1])
        )

    # Optional: decay DIRTY ages globally (no buffers)
    def decay_dirty(self) -> int:
        """
        Decrement DIRTY > 0 across all materials by 1. Returns count of decremented rows.
        """
        dec = 0
        for m in range(self.nmats):
            a = self.array[m]
            if a.size == 0:
                continue
            mask = a[:, self.DIRTY] > 0
            if np.any(mask):
                a2 = a.copy()
                a2[mask, self.DIRTY] = a2[mask, self.DIRTY] - 1
                self.array[m] = a2
                dec += int(np.sum(mask))
        return int(dec)

    # ============================================================
    # SPLIT (in-place apply, returns None)
    # ============================================================

    def split(self, pos: POS, mat: int, pos1: POS | None = None) -> None:
        if pos is None:
            raise ValueError("pos must be provided")
        if mat is None:
            raise ValueError("mat must be provided")

        found_mat: int | None = None
        found_idx: int | None = None

        # Prefer Search
        bid = self.search.find(pos=pos)
        if bid is not None:
            loc = self._loc.get(int(bid))
            if loc is not None:
                m0, i0 = loc
                m0 = int(m0)
                i0 = int(i0)
                a0 = self.array[m0]
                if 0 <= i0 < int(a0.shape[0]):
                    row0 = a0[i0]
                    x, y, z = pos
                    if (row0[self.X0] <= x < row0[self.X1] and
                        row0[self.Y0] <= y < row0[self.Y1] and
                        row0[self.Z0] <= z < row0[self.Z1]):
                        found_mat = m0
                        found_idx = i0

        # Fallback scan (kept as last resort)
        if found_mat is None or found_idx is None:
            for m in range(self.nmats):
                a = self.array[m]
                if a.size == 0:
                    continue
                idx = np.flatnonzero(self.contains(pos=pos, mat=m))
                if idx.size:
                    found_mat = int(m)
                    found_idx = int(idx[0])
                    break

        if found_mat is None or found_idx is None:
            return

        # remove old row (swap-delete)
        a = self.array[found_mat]
        old_row = a[found_idx].copy()
        old_id = int(old_row[self.ID])

        last_idx = int(a.shape[0] - 1)
        if found_idx != last_idx:
            moved = a[last_idx].copy()
            a[found_idx] = moved
            self._loc[int(moved[self.ID])] = (found_mat, found_idx)

        self.array[found_mat] = a[:-1]
        self._loc.pop(old_id, None)

        # split children
        target = Box.from_row(row=old_row)
        children_by_mat = target.split(pos=pos, pos1=pos1, mat=mat)

        flat_new_rows_list: list[np.ndarray] = []

        for cm, childs in children_by_mat.items():
            if not childs:
                continue
            cm = int(cm)

            new = np.empty((len(childs), 9), dtype=Config.DTYPE)
            for j, c in enumerate(childs):
                r = c.row.astype(Config.DTYPE, copy=True)
                r[self.ID] = self.getid()
                r[self.MAT] = cm
                # mark as dirty (max)
                r[self.DIRTY] = self.DIRTY_TTL - 1
                new[j] = r

            base = int(self.array[cm].shape[0])
            self.array[cm] = np.vstack((self.array[cm], new))

            for k in range(int(new.shape[0])):
                rid = int(new[k, self.ID])
                self._loc[rid] = (cm, base + k)

            flat_new_rows_list.append(new)

        flat_new_rows = np.vstack(flat_new_rows_list) if flat_new_rows_list else np.zeros((0, 9), dtype=Config.DTYPE)

        # Search update
        if flat_new_rows.size:
            self.search.handle(delrow=old_row, addrows=flat_new_rows)

            
    @staticmethod
    def getaxis(axis: int):
        if axis == Config.AXIS["x"]:
            return Config.X0, Config.X1, (Config.Y0, Config.Y1, Config.Z0, Config.Z1, Config.MAT)
        if axis == Config.AXIS["y"]:
            return Config.Y0, Config.Y1, (Config.X0, Config.X1, Config.Z0, Config.Z1, Config.MAT)
        if axis == Config.AXIS["z"]:
            return Config.Z0, Config.Z1, (Config.X0, Config.X1, Config.Y0, Config.Y1, Config.MAT)
        raise ValueError("axis must be 0,1,2")

    @staticmethod
    def merge_axis(rows: np.ndarray, axis: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns:
          out_rows: merged result for provided rows
          old_rows: rows to UNREGISTER/REMOVE (full segments)
          new_rows: replacement merged rows to REGISTER/APPEND (keeps first row ID)
        """
        if rows is None:
            raise ValueError("rows must be provided")
        if rows.size == 0:
            z = np.zeros((0, 9), dtype=Config.DTYPE)
            return rows, z, z

        s, e, keys = Boxes.getaxis(axis=axis)

        order = np.lexsort([rows[:, k] for k in (s, *keys[::-1])])
        b = rows[order]
        if b.shape[0] == 0:
            z = np.zeros((0, 9), dtype=Config.DTYPE)
            return b, z, z

        same = np.ones(len(b), bool)
        for k in keys:
            same &= (b[:, k] == np.roll(b[:, k], 1))
        same[0] = False

        contig = (b[:, s] == np.roll(b[:, e], 1))
        contig[0] = False

        breaks = ~(same & contig)
        starts = np.flatnonzero(breaks)
        ends = np.r_[starts[1:] - 1, len(b) - 1]

        out_list: list[np.ndarray] = []
        old_list: list[np.ndarray] = []
        new_list: list[np.ndarray] = []

        for st, en in zip(starts, ends):
            st = int(st)
            en = int(en)

            if st == en:
                out_list.append(b[st].copy())
                continue

            seg = b[st:en + 1]
            old_list.append(seg.copy())

            merged = seg[0].copy()
            merged[e] = seg[-1, e]

            # DIRTY rule: merged DIRTY is max of segment (covers "if any max -> max")
            merged[Boxes.DIRTY] = int(np.max(seg[:, Boxes.DIRTY]))

            out_list.append(merged.copy())
            new_list.append(merged.copy())

        out_rows = np.vstack(out_list) if out_list else np.zeros((0, 9), dtype=Config.DTYPE)
        old_rows = np.vstack(old_list) if old_list else np.zeros((0, 9), dtype=Config.DTYPE)
        new_rows = np.vstack(new_list) if new_list else np.zeros((0, 9), dtype=Config.DTYPE)

        return out_rows, old_rows, new_rows

    def _remove_ids_from_material(self, mat: int, ids: set[int]) -> np.ndarray:
        """
        Remove given ids from self.array[mat] using swap-delete, updating self._loc.
        Returns the removed rows as an ndarray (n,9) (for Search delrows).
        """
        mat = int(mat)
        if not ids:
            return np.zeros((0, 9), dtype=Config.DTYPE)

        a = self.array[mat]
        removed: list[np.ndarray] = []

        for rid in list(ids):
            loc = self._loc.get(int(rid))
            if loc is None:
                continue
            m0, idx0 = loc
            if int(m0) != mat:
                continue

            idx0 = int(idx0)
            if idx0 < 0 or idx0 >= int(a.shape[0]):
                # mapping might be stale; skip (Search is still authoritative)
                continue

            row_old = a[idx0].copy()
            removed.append(row_old)

            last = int(a.shape[0] - 1)
            if idx0 != last:
                moved = a[last].copy()
                a[idx0] = moved
                self._loc[int(moved[self.ID])] = (mat, idx0)

            a = a[:-1]
            self._loc.pop(int(rid), None)

        self.array[mat] = a
        return np.vstack(removed) if removed else np.zeros((0, 9), dtype=Config.DTYPE)

    def _append_rows_to_material(self, mat: int, rows: np.ndarray) -> None:
        mat = int(mat)
        if rows is None or rows.size == 0:
            return

        base = int(self.array[mat].shape[0])
        self.array[mat] = np.vstack((self.array[mat], rows))

        for i in range(int(rows.shape[0])):
            rid = int(rows[i, self.ID])
            self._loc[rid] = (mat, base + i)

    def merge(self, mat: int, rows: np.ndarray | None = None) -> None:
        if rows is None:
            rows = self.array[mat]
        if rows is None or rows.size == 0:
            return
        if not np.all(rows[:, self.MAT] == mat):
            raise ValueError("merge(mat, rows): rows must all have MAT == mat")

        old_all = np.zeros((0, 9), dtype=Config.DTYPE)
        new_all = np.zeros((0, 9), dtype=Config.DTYPE)

        while True:
            n0 = int(rows.shape[0])

            for ax in (0, 1, 2):
                rows, old_rows, new_rows = Boxes.merge_axis(rows=rows, axis=ax)
                if old_rows.size:
                    old_all = np.vstack((old_all, old_rows))
                if new_rows.size:
                    new_all = np.vstack((new_all, new_rows))

            if int(rows.shape[0]) == n0:
                break

        if old_all.size == 0 and new_all.size == 0:
            return

        # 1) Search: old out, new in
        self.search.handle(delrows=old_all, addrows=new_all)

        # 2) Array: remove affected ids, append replacements
        old_ids = set(int(x) for x in old_all[:, self.ID]) if old_all.size else set()
        new_ids = set(int(x) for x in new_all[:, self.ID]) if new_all.size else set()

        # Remove everything from old segments (including kept first ids), then re-add merged rows.
        removed_rows = self._remove_ids_from_material(mat, old_ids)

        # Append new merged rows
        self._append_rows_to_material(mat, new_all)

        # Note: we do NOT return anything. Job is done.
