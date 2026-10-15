"""WinUx app icons: pixel-art versions of app logos, drawn from simple shapes
on a 16x16 grid and given a black pixel outline (the Deltarune look).

Each icon is a function that paints a Canvas. build_app_icons() writes them
as .ico files into generated/app-icons/.
"""
import math
from pathlib import Path

import pixelart as px

OUT = Path(__file__).resolve().parent / "generated" / "app-icons"
N = 16

PALETTE = {
    "X": (0, 0, 0, 255),          # outline
    "K": (20, 20, 28, 255),       # near-black
    "W": (250, 250, 250, 255),
    "L": (190, 196, 206, 255),    # light grey
    "R": (219, 68, 55, 255),      # chrome red
    "Y": (244, 180, 0, 255),      # chrome yellow
    "G": (15, 157, 88, 255),      # chrome green
    "B": (66, 133, 244, 255),     # chrome blue
    "F": (255, 200, 60, 255),     # folder yellow
    "f": (230, 160, 30, 255),     # folder shade
    "U": (0, 120, 212, 255),      # windows / explorer blue
    "O": (217, 119, 87, 255),     # claude orange
    "C": (255, 136, 0, 255),      # vlc orange
    "P": (88, 101, 242, 255),     # discord blurple
    "S": (30, 215, 96, 255),      # spotify green
    "H": (255, 26, 26, 255),      # soul red
    "V": (40, 20, 70, 255),       # deltarune purple-black
    "N": (23, 44, 74, 255),       # steam navy
    "1": (241, 80, 34, 255),      # old Windows logo: red
    "2": (124, 187, 0, 255),      #   green
    "3": (0, 164, 239, 255),      #   blue
    "4": (255, 185, 0, 255),      #   yellow
    "a": (255, 165, 0, 255),      # the 7 souls: orange (bravery)
    "b": (255, 255, 0, 255),      #   yellow (justice)
    "c": (0, 192, 0, 255),        #   green (kindness)
    "d": (66, 252, 255, 255),     #   cyan (patience)
    "e": (0, 60, 255, 255),       #   blue (integrity)
    "g": (213, 53, 217, 255),     #   purple (perseverance)
    "z": (45, 140, 255, 255),     # zoom blue
    "p": (55, 118, 171, 255),     # python blue
    "q": (255, 212, 59, 255),     # python yellow
    "m": (130, 130, 145, 255),    # task view grey
}


class Canvas:
    def __init__(self):
        self.px = [["." for _ in range(N)] for _ in range(N)]

    def put(self, x, y, c):
        if 0 <= x < N and 0 <= y < N:
            self.px[y][x] = c

    def each(self):
        for y in range(N):
            for x in range(N):
                yield x, y, x + 0.5, y + 0.5   # pixel centers

    def circle(self, cx, cy, r, c):
        for x, y, px_, py in self.each():
            if (px_ - cx) ** 2 + (py - cy) ** 2 <= r * r:
                self.put(x, y, c)

    def ring(self, cx, cy, r, width, c):
        for x, y, px_, py in self.each():
            if abs(math.hypot(px_ - cx, py - cy) - r) <= width / 2:
                self.put(x, y, c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, c)

    def poly(self, pts, c):
        for x, y, px_, py in self.each():
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py) != (yj > py) and px_ < (xj - xi) * (py - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                self.put(x, y, c)

    def line(self, x0, y0, x1, y1, width, c):
        for x, y, px_, py in self.each():
            dx, dy = x1 - x0, y1 - y0
            t = max(0, min(1, ((px_ - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
            if math.hypot(px_ - (x0 + t * dx), py - (y0 + t * dy)) <= width / 2:
                self.put(x, y, c)

    def outline(self):
        """Black outline around everything (the WinUx pixel look)."""
        grid = [row[:] for row in self.px]
        for y in range(N):
            for x in range(N):
                if self.px[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < N and 0 <= yy < N and self.px[yy][xx] not in ".X":
                        grid[y][x] = "X"
                        break
        self.px = grid

    def rows(self):
        return ["".join(r) for r in self.px]


# ------------------------------------------------------------------ the icons
# Shapes stay 1px inside the edge so the outline fits.

def chrome(c):
    cx = cy = 8
    for x, y, px_, py in c.each():
        d = math.hypot(px_ - cx, py - cy)
        if d > 7:
            continue
        a = math.degrees(math.atan2(py - cy, px_ - cx)) % 360
        c.put(x, y, "R" if 210 <= a < 330 else ("G" if 90 <= a < 210 else "Y"))
    c.circle(cx, cy, 3.4, "W")
    c.circle(cx, cy, 2.5, "B")


def folder_shape(c, front="F"):
    c.rect(1, 3, 6, 4, "f")          # tab
    c.rect(1, 4, 14, 13, "f")        # back
    c.rect(1, 6, 14, 13, front)      # front


def files(c):
    folder_shape(c)
    c.rect(1, 11, 14, 12, "U")       # File Explorer's blue stripe


def folder(c):
    folder_shape(c)
    c.rect(2, 7, 13, 7, "W")         # a little shine


def claude(c):
    # Claude's sparkle: 8 thin rays with gaps between them
    for i in range(8):
        a = math.radians(i * 45)
        c.line(8, 8, 8 + math.cos(a) * 6.8, 8 + math.sin(a) * 6.8, 1.5, "O")
    c.circle(8, 8, 1.6, "O")


def vlc(c):
    c.poly([(8, 1), (3.2, 12), (12.8, 12)], "C")
    c.rect(1, 12, 14, 14, "C")
    for y0 in (5, 9):                 # the white stripes
        for x, y, px_, py in c.each():
            if y in (y0, y0 + 1) and c.px[y][x] == "C":
                c.put(x, y, "W")


def discord(c):
    c.rect(1, 2, 14, 13, "P")
    for x, y in ((1, 2), (14, 2), (1, 13), (14, 13)):
        c.put(x, y, ".")
    # Clyde: white face, little ears, blurple eyes
    c.circle(8, 8.4, 4.6, "W")
    c.rect(3, 5, 4, 7, "W")
    c.rect(11, 5, 12, 7, "W")
    c.rect(3, 9, 12, 10, "W")
    c.circle(6, 8.2, 1.15, "P")
    c.circle(10, 8.2, 1.15, "P")


def paint(c, rows):
    """Lay a hand-drawn grid on top ('.' = leave as is)."""
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                c.put(x, y, ch)


def spotify(c):
    c.circle(8, 8, 7, "S")
    paint(c, [
        "................",
        "................",
        "................",
        "................",
        "................",
        "....KKKKKKKK....",
        "...K........K...",
        "................",
        ".....KKKKKK.....",
        "....K......K....",
        "................",
        "......KKKK......",
        ".....K....K.....",
    ])


def roblox(c):
    a = math.radians(15)

    def sq(half):
        return [(8 + math.cos(a + k * math.pi / 2) * half * 1.414,
                 8 + math.sin(a + k * math.pi / 2) * half * 1.414) for k in range(4)]
    c.poly(sq(5.6), "W")
    c.poly(sq(1.6), "K")


def deltarune(c):
    c.rect(1, 1, 14, 14, "V")
    paint(c, [                        # the Delta Rune: winged sphere, three triangles
        "................",
        "................",
        "..W..........W..",
        "..WW..WWWW..WW..",
        "...WWWWWWWWWW...",
        "......WWWW......",
        "................",
        "................",
        "..WWW.WWWW.WWW..",
        "...W..WWWW..W...",
        ".......WW.......",
        ".......WW.......",
    ])


def undertale(c):
    c.poly([(8, 14), (1.2, 7), (1.2, 4), (3.5, 1.8), (5.8, 1.8), (8, 4.2),
            (10.2, 1.8), (12.5, 1.8), (14.8, 4), (14.8, 7)], "H")


def windows(c):
    # the classic four-color Windows logo
    for (x0, y0), col in (((1, 1), "1"), ((9, 1), "2"), ((1, 9), "3"), ((9, 9), "4")):
        c.rect(x0, y0, x0 + 5, y0 + 5, col)


def search(c):
    c.ring(6.5, 6.5, 4.2, 1.8, "W")
    c.line(9.6, 9.6, 13.6, 13.6, 2.4, "W")


def steam(c):
    c.circle(8, 8, 7, "N")
    c.ring(10.3, 5.8, 2.1, 1.3, "W")                 # the piston
    c.circle(10.3, 5.8, 0.9, "W")
    c.circle(5, 11, 1.7, "W")
    c.line(5, 11, 9.2, 7.2, 1.3, "W")


def lively(c):
    # Lively Wallpaper: the 7 human souls, red (determination) in the middle
    def heart(x, y, col):
        paint(c, [""] * y + ["." * x + col + "." + col,
                             "." * x + col * 3,
                             "." * x + "." + col])
    heart(6, 6, "H")
    for (x, y), col in (((6, 1), "a"), ((11, 3), "b"), ((11, 9), "c"),
                        ((6, 11), "d"), ((1, 9), "e"), ((1, 3), "g")):
        heart(x, y, col)


def zoom(c):
    c.rect(1, 1, 14, 14, "z")
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):
        c.put(x, y, ".")
    c.rect(3, 5, 9, 10, "W")                       # the camera body
    c.poly([(9.5, 7.5), (13, 5), (13, 11), (9.5, 8.5)], "W")   # and its lens


def python(c):
    paint(c, [                                     # two snakes: blue on top, yellow below
        "................",
        ".....pppppp.....",
        "....pWpppppp....",
        "....pppppppp....",
        "........pppp....",
        "..pppppppppp.qq.",
        ".ppppppppppp.qqq",
        ".ppppppppppp.qqq",
        ".ppp.qqqqqqqqqqq",
        ".ppp.qqqqqqqqqqq",
        "..pp.qqqqqqqqqq.",
        "....qqqq........",
        "....qqqqqqqq....",
        "....qqqqqqWq....",
        ".....qqqqqq.....",
    ])


def taskview(c):
    c.rect(5, 2, 14, 10, "m")                      # back window
    c.rect(6, 4, 13, 9, "K")
    c.rect(1, 6, 10, 14, "W")                      # front window
    c.rect(1, 6, 10, 7, "L")


def controller(c):
    c.poly([(2, 5), (14, 5), (15.5, 12), (12.5, 13), (10.5, 10), (5.5, 10), (3.5, 13), (0.5, 12)], "L")
    c.rect(3, 7, 5, 7, "K")                        # d-pad
    c.rect(4, 6, 4, 8, "K")
    c.put(11, 6, "H")                              # buttons
    c.put(12, 7, "U")
    c.put(10, 7, "S")
    c.put(11, 8, "Y")


ICONS = {
    "chrome": ("Chrome", chrome), "files": ("File Explorer", files), "folder": ("Folders", folder),
    "claude": ("Claude", claude), "vlc": ("VLC", vlc), "discord": ("Discord", discord),
    "spotify": ("Spotify", spotify), "roblox": ("Roblox", roblox), "deltarune": ("DELTARUNE", deltarune),
    "undertale": ("UNDERTALE", undertale), "windows": ("Windows", windows), "search": ("Search", search),
    "steam": ("Steam", steam), "lively": ("Lively Wallpaper", lively),
    "zoom": ("Zoom", zoom), "python": ("Python", python), "taskview": ("Task View", taskview),
    "controller": ("Games", controller),
}


def draw(name):
    c = Canvas()
    ICONS[name][1](c)
    c.outline()
    return c.rows()


def build_app_icons():
    """Write every app icon as an .ico; returns {name: path}."""
    from assets import write_if_changed
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in ICONS:
        rows = draw(name)
        images = [px.render(rows, PALETTE, s) for s in (16, 3, 2, 1)]   # 256, 48, 32, 16
        p = OUT / f"{name}.ico"
        write_if_changed(p, px.ico(images))
        paths[name] = str(p)
    return paths


def taskbar_png(name, path, scale=2, canvas=48):
    """A PNG with the icon centered on a bigger see-through square, so Taskbar
    Styler can stretch it to the button size and it still looks icon-sized."""
    w, h, d = px.render(draw(name), PALETTE, scale)
    out = bytearray(canvas * canvas * 4)
    ox, oy = (canvas - w) // 2, (canvas - h) // 2
    for y in range(h):
        out[((y + oy) * canvas + ox) * 4:((y + oy) * canvas + ox + w) * 4] = d[y * w * 4:(y + 1) * w * 4]
    Path(path).write_bytes(px.png(canvas, canvas, bytes(out)))
    return str(path)


def preview_png(path, scale=6, gap=12):
    """One PNG with every icon side by side (for the panel / checking)."""
    imgs = [px.render(draw(n), PALETTE, scale) for n in ICONS]
    W = sum(w for w, _, _ in imgs) + gap * (len(imgs) - 1)
    H = max(h for _, h, _ in imgs)
    out = bytearray(W * H * 4)
    ox = 0
    for w, h, d in imgs:
        for y in range(h):
            out[(y * W + ox) * 4:(y * W + ox + w) * 4] = d[y * w * 4:(y + 1) * w * 4]
        ox += w + gap
    Path(path).write_bytes(px.png(W, H, bytes(out)))


if __name__ == "__main__":
    for n in ICONS:
        print(n)
        print("\n".join(draw(n)))
