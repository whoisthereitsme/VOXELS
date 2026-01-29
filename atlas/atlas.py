from __future__ import annotations

import math
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image


# ============================================================
# Quantized levels
# ============================================================

def levels(n: int) -> List[int]:
    if n <= 0:
        raise ValueError("n must be > 0")
    return [int(min(i * 256 / n, 255)) for i in range(n + 1)]


# ============================================================
# Color ordering: grouped by "dominant channels" then by brightness
# - grayscale first (r=g=b)
# - then dominant channel groups: r, g, b, rg, rb, gb, rgb
# - within group: sort by brightness (r+g+b), then by components for stability
# ============================================================

def _dominance_key(r: int, g: int, b: int) -> str:
    # exact grayscale
    if r == g == b:
        return "gray"

    # Determine max and ties among channels
    m = max(r, g, b)
    top = []
    if r == m:
        top.append("r")
    if g == m:
        top.append("g")
    if b == m:
        top.append("b")

    # If single dominant: "r"/"g"/"b"
    if len(top) == 1:
        return top[0]

    # Tie of two: "rg"/"rb"/"gb"
    if len(top) == 2:
        return "".join(top)

    # All equal handled above, but keep safe:
    return "rgb"


def colors_grouped(lvls: List[int], factor: float = 1.0) -> List[Tuple[int, int, int, int]]:
    """
    Produce all RGB combinations from lvls, apply factor, then order:
      gray -> r/g/b -> rg/rb/gb -> rgb
    and sort inside each group by brightness.
    """
    groups: Dict[str, List[Tuple[int, int, int, int]]] = {
        "gray": [],
        "r": [], "g": [], "b": [],
        "rg": [], "rb": [], "gb": [],
        "rgb": [],
    }

    for rr in lvls:
        for gg in lvls:
            for bb in lvls:
                r = int(rr * factor)
                g = int(gg * factor)
                b = int(bb * factor)
                a = 255
                k = _dominance_key(r, g, b)
                groups[k].append((r, g, b, a))

    # Sort within each group: brightness then lexicographic
    def inner_sort_key(c: Tuple[int, int, int, int]):
        r, g, b, _ = c
        return (r + g + b, r, g, b)

    ordered_keys = ["gray", "r", "g", "b", "rg", "rb", "gb", "rgb"]

    out: List[Tuple[int, int, int, int]] = []
    for k in ordered_keys:
        groups[k].sort(key=inner_sort_key)
        out.extend(groups[k])

    return out


# ============================================================
# Pretty JSON writer: objects indented, lists always single-line
# ============================================================

def pretty_obj(
    f,
    obj: Dict[str, Any],
    indent: int = 4,
    level: int = 1,
) -> None:
    pad = " " * (indent * level)
    pad0 = " " * (indent * (level - 1))

    f.write("{\n")
    items = list(obj.items())

    for i, (k, v) in enumerate(items):
        f.write(f'{pad}"{k}": ')
        if isinstance(v, list):
            # lists single-line, with a space after comma for readability
            f.write(json.dumps(v, separators=(", ", ":")))
        else:
            f.write(json.dumps(v))
        if i < len(items) - 1:
            f.write(",")
        f.write("\n")

    f.write(pad0 + "}")


# ============================================================
# Atlas generator
# ============================================================

def make_atlas(
    tile_size: int = 64,
    out_png: str = "atlas.png",
    out_json: str = "atlas.json",
    nlevels: int = 8,     # IMPORTANT: this is "n" for levels(n) => returns n+1 channel values
    factor: float = 0.5,
) -> tuple[Path, Path]:
    lvls = levels(n=nlevels)

    cols1 = colors_grouped(lvls=lvls, factor=1.0)
    cols0 = colors_grouped(lvls=lvls, factor=factor)

    if len(cols1) != len(cols0):
        raise RuntimeError("color list mismatch")

    nt = len(cols1)
    # You want a perfect square grid often; if not a square, we still pack into a square with empty tiles.
    nside = math.ceil(math.sqrt(nt))
    nrows = nside
    ncols = nside

    sizex = ncols * tile_size
    sizey = nrows * tile_size

    print(f"Generating atlas: nlevels={nlevels} => channel values={len(lvls)} => tiles={nt}")
    print(f"Grid: {ncols} x {nrows} => PNG: {sizex} x {sizey}")

    img = Image.new("RGBA", (sizex, sizey), (0, 0, 0, 0))

    data: Dict[int, Dict[str, Any]] = {}

    for i, (c1, c0) in enumerate(zip(cols1, cols0)):
        col = i % ncols
        row = i // ncols

        x0 = col * tile_size
        y0 = row * tile_size
        x1 = x0 + tile_size - 1
        y1 = y0 + tile_size - 1

        # Edge first, then inner
        img.paste(c0, (x0, y0, x1, y1))
        img.paste(c1, (x0 + 1, y0 + 1, x1 - 1, y1 - 1))

        data[i] = {
            "index": i,
            "color0": [c0[0], c0[1], c0[2], c0[3]],
            "color1": [c1[0], c1[1], c1[2], c1[3]],
            "pos": [x0, y0],
            "bounds": [x0, y0, x1, y1],
            "size": [tile_size, tile_size],
        }

    # JSON write: objects indented, lists one-line
    with open(out_json, "w", encoding="utf-8") as f:
        f.write("{\n")
        items = list(data.items())
        for i, (k, v) in enumerate(items):
            f.write(f'  "{k}": ')
            pretty_obj(f, v, indent=4, level=2)
            if i < len(items) - 1:
                f.write(",")
            f.write("\n")
        f.write("}\n")

    out_png_p = Path(out_png).resolve()
    out_json_p = Path(out_json).resolve()
    img.save(out_png_p, "PNG")
    print(f"Wrote: {out_png_p}")
    print(f"Wrote: {out_json_p}")
    return out_png_p, out_json_p


# ============================================================
# Best nlevels chooser under a max MB budget, requiring perfect square fill:
# You originally required ntiles == ncolors with nrows==ncols==ceil(sqrt(ncolors)).
# This only happens when ncolors is a perfect square; for (lvl+1)^3 this means (lvl+1) is a square.
# We keep that constraint here because you said it "aligns perfectly."
# ============================================================

def best_squarecube_nlevels(
    tile_size: int,
    max_megabyte: int,
    max_search: int = 256,
) -> int:
    max_bytes = max_megabyte * 1024 * 1024
    tile_bytes = tile_size * tile_size * 4
    max_tiles = max_bytes // tile_bytes

    matches: List[int] = []
    for lvl in range(0, max_search):
        ncolors = (lvl + 1) ** 3
        nside = math.isqrt(ncolors)
        if nside * nside == ncolors:  # perfect square => perfect nside x nside fill
            if ncolors <= max_tiles:
                matches.append(lvl)

    if not matches:
        raise RuntimeError("No square-cube level fits the given memory budget.")

    return matches[-1]


if __name__ == "__main__":
    # User-style configuration
    tile_size = 64
    max_megabyte = 16

    best_lvl = best_squarecube_nlevels(tile_size=tile_size, max_megabyte=max_megabyte)
    print(f"Best square-cube nlevels under {max_megabyte}MB @ tile_size={tile_size}: {best_lvl}")
    print(f"Tiles = (best_lvl+1)^3 = {(best_lvl+1)**3}")

    make_atlas(
        tile_size=tile_size,
        out_png="atlas.png",
        out_json="atlas.json",
        nlevels=best_lvl,
        factor=0.5,
    )
