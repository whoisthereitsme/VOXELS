# mine.py
from __future__ import annotations

from typing import Any, Iterator


class Mine:
    mineidx = 0

    def __init__(self, x: int = None, y: int = None, z: int = None, sx: int = None, sy: int = None, sz: int = None) -> None:
        if x is None or y is None or z is None or sx is None or sy is None or sz is None:
            raise ValueError("x,y,z,sx,sy,sz must be provided")

        self.pos = (int(x), int(y), int(z))
        self.sx = int(sx)
        self.sy = int(sy)
        self.sz = int(sz)
        self.world_min_z = 0

        self.id = int(Mine.mineidx)
        Mine.mineidx += 1
        self.nextframe = int(self.id % 60)

        self.pos0 = (self.pos[0] - self.sx, self.pos[1] - self.sy, self.pos[2] - self.sz)
        self.pos1 = (self.pos[0] + self.sx, self.pos[1] + self.sy, self.pos[2])

        self._reset_layer_state()
        self.exhausted: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None

    def _iter_ring(self, z: int = None, r: int = None) -> Iterator[tuple[int, int, int]]:
        if z is None or r is None:
            raise ValueError("z and r must be provided")

        cx, cy, _ = self.pos
        x0, y0, _ = self.pos0
        x1, y1, _ = self.pos1

        def inside(xx: int, yy: int) -> bool:
            return (x0 <= xx < x1) and (y0 <= yy < y1)

        if r == 0:
            if inside(cx, cy):
                yield (cx, cy, z)
            return

        yt = cy - r
        for xx in range(cx - r, cx + r + 1):
            if inside(xx, yt):
                yield (xx, yt, z)

        xr = cx + r
        for yy in range(cy - r + 1, cy + r + 1):
            if inside(xr, yy):
                yield (xr, yy, z)

        yb = cy + r
        for xx in range(cx + r - 1, cx - r - 1, -1):
            if inside(xx, yb):
                yield (xx, yb, z)

        xl = cx - r
        for yy in range(cy + r - 1, cy - r, -1):
            if inside(xl, yy):
                yield (xl, yy, z)

    def _reset_layer_state(self) -> None:
        x0, y0, z0 = self.pos0
        x1, y1, z1 = self.pos1

        self._z = int(z1 - 1)
        self._z_min = int(z0)

        self._r = 0
        self._r_max = int(max(self.sx, self.sy))
        self._ring_iter: Iterator[tuple[int, int, int]] | None = None

    def _layer_has_work(self) -> bool:
        _x0, _y0, z0 = self.pos0
        _x1, _y1, z1 = self.pos1
        return not (z1 <= self.world_min_z or z0 < self.world_min_z)

    def _next_coord_in_current_region(self) -> tuple[int, int, int] | None:
        if not self._layer_has_work():
            return None

        while True:
            if self._z < self._z_min:
                return None

            if self._ring_iter is None:
                self._ring_iter = self._iter_ring(z=self._z, r=self._r)

            try:
                return next(self._ring_iter)
            except StopIteration:
                self._ring_iter = None
                self._r += 1

                if self._r > self._r_max:
                    self._z -= 1
                    self._r = 0
                    self._ring_iter = None

    def shift(self) -> None:
        x0, y0, z0 = self.pos0
        x1, y1, z1 = self.pos1

        z0 -= self.sz
        z1 -= self.sz
        self.pos0 = (x0, y0, z0)
        self.pos1 = (x1, y1, z1)
        self._reset_layer_state()

        if not self._layer_has_work():
            self.exhausted = (self.pos0, self.pos1)

            x0, y0, _ = self.pos0
            x1, y1, _ = self.pos1

            x0 -= 1
            y0 -= 1
            x1 += 1
            y1 += 1

            z1 = 0
            z0 = z1 - self.sz

            self.pos0 = (x0, y0, z0)
            self.pos1 = (x1, y1, z1)

            self.sx += 1
            self.sy += 1

            self._reset_layer_state()

            if not self._layer_has_work():
                self.exhausted = (self.pos0, self.pos1)

    def next(self, frame: int = None) -> None | tuple[int, int, int] | Any:
        if frame is None:
            frame = 0

        if (frame % 60) != self.nextframe:
            return None

        while True:
            coord = self._next_coord_in_current_region()
            if coord is not None:
                return coord
            self.shift()
            if self.exhausted is not None and not self._layer_has_work():
                return None
