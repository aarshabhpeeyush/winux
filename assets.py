"""WinUx's own pixel cursors, desktop icons and chiptune sounds.
Everything is drawn here as text grids / notes and turned into real files by pixelart.py."""

from pathlib import Path

import pixelart as px

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 26, 26)
YELLOW = (255, 230, 0)


def grid(rows, size=16):
    """Pad a grid out to size x size so every image is square."""
    rows = [r.ljust(size, ".")[:size] for r in rows]
    return rows + ["." * size] * (size - len(rows))


def outlined(shape, fill="W", line="X", scale=1):
    """Take a 0/1 shape, scale it up and wrap it in a 1-pixel outline."""
    big = ["".join(c * scale for c in row) for row in shape for _ in range(scale)]
    h, w = len(big) + 2, len(big[0]) + 2
    cells = [["."] * w for _ in range(h)]
    for y, row in enumerate(big):
        for x, c in enumerate(row):
            if c == "1":
                cells[y + 1][x + 1] = fill
    for y in range(h):
        for x in range(w):
            if cells[y][x] == "." and any(
                    0 <= y + dy < h and 0 <= x + dx < w and cells[y + dy][x + dx] == fill
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                cells[y][x] = line
    return ["".join(r) for r in cells]


def center(rows, size=16):
    """Center a smaller grid inside size x size."""
    h, w = len(rows), max(len(r) for r in rows)
    top, left = (size - h) // 2, (size - w) // 2
    out = ["." * size] * top + ["." * left + r.ljust(w, ".") for r in rows]
    return grid(out, size)


# ---------------------------------------------------------------- cursor art

ARROW = grid([
    "X...............",
    "XX..............",
    "XWX.............",
    "XWWX............",
    "XWWWX...........",
    "XWWWWX..........",
    "XWWWWWX.........",
    "XWWWWWWX........",
    "XWWWWWWWX.......",
    "XWWWWWWWWX......",
    "XWWWWWXXXXX.....",
    "XWWXWWX.........",
    "XWX.XWWX........",
    "XX..XWWX........",
    "X....XWWX.......",
    ".....XXXX.......",
])

HAND = grid([
    ".....XX.........",
    "....XWWX........",
    "....XWWX........",
    "....XWWX........",
    "....XWWXXX......",
    "....XWWXWWXXX...",
    ".XX.XWWXWWXWWXX.",
    "XWWXXWWWWWWWWWWX",
    "XWWWXWWWWWWWWWWX",
    ".XWWWWWWWWWWWWWX",
    "..XWWWWWWWWWWWWX",
    "..XWWWWWWWWWWWX.",
    "...XWWWWWWWWWWX.",
    "....XWWWWWWWWX..",
    "....XWWWWWWWWX..",
    "....XXXXXXXXXX..",
])

IBEAM = grid([
    "....XXX.XXX.....",
    "....XWWXWWX.....",
    "....XXXWXXX.....",
    *["......XWX......."] * 10,
    "....XXXWXXX.....",
    "....XWWXWWX.....",
    "....XXX.XXX.....",
])

SOUL = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
HEART = center(outlined(SOUL, fill="W", scale=2))


def star_shape(arm):
    """A 4-point save-point sparkle with arms `arm` pixels long (15x15)."""
    rows = []
    for y in range(15):
        row = ""
        for x in range(15):
            dx, dy = abs(x - 7), abs(y - 7)
            inside = (dx == 0 and dy <= arm) or (dy == 0 and dx <= arm) or (dx + dy <= max(1, arm // 2))
            row += "1" if inside else "0"
        rows.append(row)
    # trim empty border so outline fits
    rows = [r for r in rows if "1" in r]
    cols = [i for i in range(15) if any(r[i] == "1" for r in rows)]
    return [r[cols[0]:cols[-1] + 1] for r in rows]


STAR_FRAMES = [center(outlined(star_shape(a), fill="W")) for a in (3, 5, 6, 5, 3, 2)]


def with_star(base, arm):
    """Arrow with a small sparkle in the bottom-right corner (for 'working in background')."""
    small = outlined(star_shape(arm), fill="S")
    out = [list(r) for r in base]
    oy, ox = 16 - len(small), 16 - len(small[0])
    for y, row in enumerate(small):
        for x, c in enumerate(row):
            if c != ".":
                out[oy + y][ox + x] = c
    return ["".join(r) for r in out]


# ---------------------------------------------------------------- icon art

THIS_PC = grid([
    "................",
    ".XXXXXXXXXXXXXX.",
    ".XGGGGGGGGGGGGX.",
    ".XG" + "K" * 10 + "GX.",
    ".XGK" + "KRRKRRK" + "KKGX.",
    ".XGK" + "RRRRRRR" + "KKGX.",
    ".XGK" + "RRRRRRR" + "KKGX.",
    ".XGK" + "KRRRRRK" + "KKGX.",
    ".XGK" + "KKRRRKK" + "KKGX.",
    ".XGK" + "KKKRKKK" + "KKGX.",
    ".XG" + "K" * 10 + "GX.",
    ".XGGGGGGGGGGGGX.",
    ".XXXXXXXXXXXXXX.",
    "......XGGX......",
    "....XGGGGGGX....",
    "....XXXXXXXX....",
])

BIN_BODY = ["...X" + "GGDGGDGG" + "X..."] * 10 + ["...XXXXXXXXXX..."]

BIN_EMPTY = grid([
    "......XXXX......",
    "...XXXXGGXXXX...",
    "..XGGGGGGGGGGX..",
    "..XXXXXXXXXXXX..",
    "...XGGGGGGGGX...",
] + BIN_BODY)

BIN_FULL = grid([
    "....WWW..WW.....",
    "...WWWWWWWWW....",
    "...WWAWWWWAW....",
    "..XXXXXXXXXXXX..",
    "...XGGGGGGGGX...",
] + BIN_BODY)

FOLDER = grid([
    "................",
    "................",
    ".XXXXX..........",
    "XYYYYYX.........",
    "XYYYYYXXXXXXXXX.",
    "XYYYYYYYYYYYYYYX",
    "XOOOOOOOOOOOOOOX",
    "XOOO" + "ORRORRO" + "OOOOX",
    "XOOO" + "RRRRRRR" + "OOOOX",
    "XOOO" + "RRRRRRR" + "OOOOX",
    "XOOO" + "ORRRRRO" + "OOOOX",
    "XOOO" + "OORRROO" + "OOOOX",
    "XOOO" + "OOOROOO" + "OOOOX",
    "XOOOOOOOOOOOOOOX",
    "XXXXXXXXXXXXXXXX",
])


def globe():
    rows = []
    for y in range(16):
        row = ""
        for x in range(16):
            dx, dy = x - 7.5, y - 7.5
            d = (dx * dx + dy * dy) ** 0.5
            if d > 7.6:
                row += "."
            elif d > 6.6:
                row += "X"
            else:
                meridian = abs(abs(dx) - 3.6 * max(0.0, 1 - (dy / 7) ** 2) ** 0.5) < 0.6
                row += "N" if abs(dx) < 0.6 or abs(dy) < 0.6 or meridian else "T"
        rows.append(row)
    return rows


NETWORK = globe()

ICON_PALETTE = {
    "X": BLACK, "G": (154, 160, 170), "K": (16, 16, 24), "R": RED, "D": (110, 116, 126),
    "W": (245, 245, 245), "A": (200, 200, 200), "Y": (255, 207, 74), "O": (242, 169, 59),
    "T": (43, 167, 184), "N": (19, 92, 105),
}

DESKTOP_ICONS = {
    "this-pc": THIS_PC,
    "bin-empty": BIN_EMPTY,
    "bin-full": BIN_FULL,
    "user-folder": FOLDER,
    "network": NETWORK,
}


# ---------------------------------------------------------------- sounds (original chiptunes)

N = px.note_freq


def snd_blip():
    return px.tone(N("A5"), 0.05, slide=2400) + px.tone(N("E6"), 0.06)


def snd_info():
    return px.tone(N("E5"), 0.08) + px.tone(N("B5"), 0.14)


def snd_warning():
    return px.tone(N("B5"), 0.09, duty=0.25) + px.tone(N("F5"), 0.16, duty=0.25)


def snd_error():  # a "hurt" crunch
    return px.mix(px.tone(220, 0.22, vol=0.25, slide=-600, duty=0.25),
                  px.tone(0, 0.12, vol=0.22, wave="noise", decay=10))


def snd_save():  # bright little save-point jingle
    seq = []
    for n in ("C5", "E5", "G5", "C6"):
        seq += px.tone(N(n), 0.07, vol=0.3)
    return px.mix(seq + px.tone(N("E6"), 0.22, vol=0.3),
                  px.rest(0.02) + px.tone(N("C4"), 0.5, vol=0.12, wave="triangle", decay=3))


def snd_heal():
    seq = []
    for n in ("G5", "B5", "D6", "G6", "D6", "G6"):
        seq += px.tone(N(n), 0.05, vol=0.25, duty=0.25)
    return seq


def snd_plug_in():
    return px.tone(N("C5"), 0.06) + px.tone(N("G5"), 0.06) + px.tone(N("C6"), 0.12)


def snd_unplug():
    return px.tone(N("C6"), 0.06) + px.tone(N("G5"), 0.06) + px.tone(N("C5"), 0.12)


def snd_alert():  # for "allow changes?" prompts
    return px.tone(N("G5"), 0.1, duty=0.25) + px.rest(0.04) + px.tone(N("G5"), 0.1, duty=0.25) + px.tone(N("D6"), 0.18, duty=0.25)


# Windows event name -> (file, maker)
SOUND_EVENTS = {
    ".Default": ("blip", snd_blip),
    "SystemAsterisk": ("info", snd_info),
    "SystemExclamation": ("warning", snd_warning),
    "SystemHand": ("error", snd_error),
    "SystemNotification": ("save", snd_save),
    "Notification.Default": ("save", snd_save),
    "DeviceConnect": ("plug-in", snd_plug_in),
    "DeviceDisconnect": ("unplug", snd_unplug),
    "WindowsUAC": ("alert", snd_alert),
    "MailBeep": ("heal", snd_heal),
}


# ---------------------------------------------------------------- building files

def _cursor_file(rows, palette, hotspot):
    return px.cur([px.render(rows, palette, s) for s in (2, 3, 4)], hotspot)


def write_if_changed(p, data):
    """Write a generated file, but leave it alone if it's already right.
    Windows keeps cursors and sounds that are in use open, so rewriting them fails."""
    try:
        if p.is_file() and p.read_bytes() == data:
            return
        p.write_bytes(data)
    except OSError:
        if not p.is_file():
            raise


def build_cursors(scheme, accent="#ffe600"):
    """Write one cursor scheme's files and return {Windows cursor role: path}."""
    folder = OUT / "cursors" / scheme
    folder.mkdir(parents=True, exist_ok=True)
    fill = WHITE
    if scheme == "pixel-accent":
        fill = px.hex_rgb(accent)
    pal = {"X": BLACK, "W": fill, "S": YELLOW}
    star_pal = {"X": BLACK, "W": YELLOW}

    files = {}

    def save(name, data):
        p = folder / name
        write_if_changed(p, data)
        return str(p)

    # accent cursors get the color in the name so Windows doesn't reuse an old copy
    tag = "-" + accent.lstrip("#") if scheme == "pixel-accent" else ""
    star = [_cursor_file(f, star_pal, (0.5, 0.5)) for f in STAR_FRAMES]
    if scheme == "soul":
        files["Arrow"] = save("soul.cur", _cursor_file(HEART, {"X": BLACK, "W": RED}, (0.5, 0.45)))
        files["Hand"] = save("soul-yellow.cur", _cursor_file(HEART, {"X": BLACK, "W": YELLOW}, (0.5, 0.45)))
        files["AppStarting"] = save("save-star.ani", px.ani(star, 7))
    else:
        files["Arrow"] = save(f"arrow{tag}.cur", _cursor_file(ARROW, pal, (0, 0)))
        files["Hand"] = save(f"hand{tag}.cur", _cursor_file(HAND, pal, (5.5 / 15, 0)))
        working = [_cursor_file(with_star(ARROW, arm), pal, (0, 0)) for arm in (1, 2, 3, 2)]
        files["AppStarting"] = save(f"working{tag}.ani", px.ani(working, 9))
    files["IBeam"] = save(f"ibeam{tag}.cur", _cursor_file(IBEAM, {"X": BLACK, "W": WHITE}, (7 / 15, 0.5)))
    files["Wait"] = save("save-star-wait.ani", px.ani(star, 7))
    return files


def build_icons():
    folder = OUT / "icons"
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, rows in DESKTOP_ICONS.items():
        images = [px.render(rows, ICON_PALETTE, s) for s in (16, 3, 2, 1)]  # 256, 48, 32, 16
        p = folder / f"{name}.ico"
        write_if_changed(p, px.ico(images))
        paths[name] = str(p)
    return paths


def build_sounds():
    folder = OUT / "sounds"
    folder.mkdir(parents=True, exist_ok=True)
    made, paths = {}, {}
    for event, (name, maker) in SOUND_EVENTS.items():
        if name not in made:
            p = folder / f"{name}.wav"
            write_if_changed(p, px.wav(maker()))
            made[name] = str(p)
        paths[event] = made[name]
    return paths


def _strip(tiles, scale=4, gap=8, bg=(0, 0, 0, 0)):
    """Lay a row of grids side by side as one PNG (for previews in the panel)."""
    rendered = [px.render(rows, pal, scale) for rows, pal in tiles]
    W = sum(w for w, _, _ in rendered) + gap * (len(rendered) - 1)
    H = max(h for _, h, _ in rendered)
    img = bytearray(bytes(bg) * (W * H))
    ox = 0
    for w, h, d in rendered:
        for y in range(h):
            for x in range(w):
                p = d[(y * w + x) * 4:(y * w + x) * 4 + 4]
                if p[3]:
                    j = (y * W + ox + x) * 4
                    img[j:j + 4] = p
        ox += w + gap
    return px.png(W, H, bytes(img))


def build_previews(accent="#ffe600"):
    folder = OUT / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    white = {"X": BLACK, "W": WHITE, "S": YELLOW}
    acc = {"X": BLACK, "W": px.hex_rgb(accent), "S": YELLOW}
    star = {"X": BLACK, "W": YELLOW}
    sets = {
        "cursors-pixel": [(ARROW, white), (HAND, white), (IBEAM, white), (STAR_FRAMES[2], star)],
        "cursors-pixel-accent": [(ARROW, acc), (HAND, acc), (IBEAM, white), (STAR_FRAMES[2], star)],
        "cursors-soul": [(HEART, {"X": BLACK, "W": RED}), (HEART, {"X": BLACK, "W": YELLOW}), (IBEAM, white), (STAR_FRAMES[2], star)],
        "icons-pixel": [(rows, ICON_PALETTE) for rows in DESKTOP_ICONS.values()],
    }
    for name, tiles in sets.items():
        write_if_changed(folder / f"{name}.png", _strip(tiles))


if __name__ == "__main__":
    build_previews()
    for scheme in ("pixel", "pixel-accent", "soul"):
        print(scheme, build_cursors(scheme))
    print(build_icons())
    print(build_sounds())
