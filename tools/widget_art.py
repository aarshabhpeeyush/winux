"""Pixel art for the Rainmeter widgets (faces, the Annoying Dog...).
Run it after changing a sprite:  python tools/widget_art.py
Writes PNGs into widgets/WinUx/@Resources/Images/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pixelart as px  # noqa: E402

OUT = ROOT / "widgets" / "WinUx" / "@Resources" / "Images"


def outlined(rows, pal):
    """Add a 1px black outline around a sprite (grows it by 1px each side)."""
    h, w = len(rows), max(len(r) for r in rows)
    g = [["."] * (w + 2) for _ in range(h + 2)]
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                g[y + 1][x + 1] = ch
    out = [row[:] for row in g]
    for y in range(h + 2):
        for x in range(w + 2):
            if g[y][x] == "." and any(
                    0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and g[y + dy][x + dx] != "."
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = "X"
    return ["".join(r) for r in out], {**pal, "X": (0, 0, 0, 255)}


def save(name, rows, pal, scale, outline=True):
    if outline:
        rows, pal = outlined(rows, pal)
    w, h, d = px.render(rows, pal, scale)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.png").write_bytes(px.png(w, h, d))


def rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


# ---------------------------------------------------------------- party faces

# Drawn from the Deltarune battle icons (the user's reference).
KRIS = [
    "....NNNNNNN.....",
    "..NNNNNNNNNNN...",
    ".NNNNNNNNNNNNN..",
    ".NNNNNNNNNNNNN..",
    ".NNNNNNNNNNNNN..",
    ".NNNLLLNNLLLNN..",
    ".NNLLLLLLLLLNN..",
    ".NNCCCCCCCCCNN..",
    ".NNCCKKKKKCCNN..",
    ".NNCCCKKKCCCNN..",
    "..NNCCCCCCCNN...",
    "....NNNNNNN.....",
]
SUSIE = [
    "...MM.MMMMM.....",
    "..MMMMMMMMMMM...",
    ".MMMMMMMMMMMMM..",
    "MMMMMMMMMMMMMMM.",
    "MMMMMMMMMMMMMMMM",
    "MMMDDMMMMMMDDMMM",
    "MMPPPPPPPPPMMMM.",
    "MMPPEPPEPPPPMMM.",
    "MMPPPPPPPPPPMMMM",
    ".MMPPTTTPPPMMMMM",
    "MM.MMTTTMMMMM.MM",
    "M..MMMMMMMM...MM",
    "....MM...MM.....",
]
RALSEI = [
    ".......GG.......",
    "......GGGG......",
    ".....GGGGGG.....",
    "..GG.GGGGGG.GG..",
    "...GGGGGGGGGG...",
    "..GGGGGGGGGGGG..",
    ".GGGGGGGGGGGGGG.",
    "GGGGGGGGGGGGGGGG",
    ".FFFFFFFFFFFFFF.",
    "FFFGGGFFFFGGGFFF",
    "FFGFFFGGGGFFFGFF",
    "FFFGGGFFFFGGGFFF",
    ".FFFFFFFFFFFFFF.",
    "..FF.FFFFFF.FF..",
]

# ---------------------------------------------------------------- the Annoying Dog
# Drawn from the user's reference. Faces LEFT. B = black outline (drawn by hand).

DOG_TOP = [
    ".B.BBBB.B........",
    "BWBWWWWBWB.......",
    "BWWWWWWWWWB......",
    "BWBWWBWWWWWB..BB.",
    "BWWWWWWWWWWWBBWB.",
    "BWWBBWWWWWWWWWWWB",
    "BWBWWBWWWWWWWWWWB",
    "BWWBBWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
]
DOG_WALK1 = DOG_TOP + [
    "BWWBWWWBBWWBWWWWB",
    "BWB.BWB..BWB.BWB.",
    ".B...B....B...B..",
]
DOG_WALK2 = DOG_TOP + [
    "BWWWBWWBBWWWBWWWB",
    ".BWB.BWB.BWB.BWB.",
    "..B...B...B...B..",
]
DOG_SLEEP = [
    ".................",
    ".................",
    ".................",
    ".................",
    ".B.BBBB.B........",
    "BWBWWWWBWB.......",
    "BWWWWWWWWWBBBBBB.",
    "BWBBWBBWWWWWWWWWB",
    "BWWBBWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    "BWWWWWWWWWWWWWWWB",
    ".BBBBBBBBBBBBBBB.",
]


def main():
    save("kris", KRIS, {"N": rgb("#1b1a5e"), "L": rgb("#6b6fd8"), "C": rgb("#5cf0f0"),
                        "K": rgb("#1b1a5e")}, 3)
    save("susie", SUSIE, {"M": rgb("#8e1f6e"), "D": rgb("#5e1047"), "P": rgb("#f08ad0"),
                          "E": rgb("#7a2aa0"), "T": rgb("#b030c0")}, 3)
    save("ralsei", RALSEI, {"G": rgb("#3cc88a"), "F": rgb("#1d1d24")}, 3)
    dog = {"W": rgb("#ffffff"), "B": rgb("#000000")}
    save("dog-walk1", DOG_WALK1, dog, 3, outline=False)
    save("dog-walk2", DOG_WALK2, dog, 3, outline=False)
    save("dog-sleep", DOG_SLEEP, dog, 3, outline=False)
    print("written to", OUT)


if __name__ == "__main__":
    main()
