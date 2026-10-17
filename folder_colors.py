"""WinUx folder colors: pixel folders in the seven soul colors (and a few more),
with optional emblems (heart, star, controller, music note).

Used two ways:
- by server.py, to add/remove the File Explorer right-click menu and show previews
- by that right-click menu itself:  pythonw folder_colors.py "<folder>" color=red
                                    pythonw folder_colors.py "<folder>" emblem=heart
                                    pythonw folder_colors.py "<folder>" reset

A folder gets its icon from a hidden desktop.ini inside it (IconResource=...).
Every folder WinUx colors is remembered in backups/folder-colors.json so
Restore / uninstall can put them all back.
"""
import ctypes
import json
import os
import sys
import winreg
from pathlib import Path

import app_icons
import pixelart as px

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated" / "folders"
LOG = ROOT / "backups" / "folder-colors.json"

# name: (menu label, front color, shade color)
COLORS = {
    "red": ("Red (Determination)", (255, 40, 40), (190, 20, 25)),
    "orange": ("Orange (Bravery)", (255, 150, 30), (205, 105, 15)),
    "yellow": ("Yellow (Justice)", (255, 225, 40), (215, 170, 20)),
    "green": ("Green (Kindness)", (40, 200, 60), (20, 145, 40)),
    "cyan": ("Cyan (Patience)", (70, 230, 240), (30, 170, 190)),
    "blue": ("Blue (Integrity)", (40, 90, 255), (25, 55, 190)),
    "purple": ("Purple (Perseverance)", (200, 70, 220), (145, 40, 165)),
    "pink": ("Pink", (255, 120, 190), (215, 75, 145)),
    "white": ("White", (245, 245, 245), (185, 190, 200)),
    "gray": ("Gray (Gaster)", (130, 135, 145), (85, 88, 98)),
}

EMBLEMS = {
    "heart": ("Heart", [
        ".XX.XX.",
        "XRRXRRX",
        "XRRRRRX",
        "XRRRRRX",
        ".XRRRX.",
        "..XRX..",
        "...X...",
    ]),
    "star": ("Star", [
        "....X....",
        "...XYX...",
        "XXXXYXXXX",
        "XYYYYYYYX",
        ".XYYYYYX.",
        "..XYYYX..",
        ".XYYXYYX.",
        ".XYX.XYX.",
        ".XX...XX.",
    ]),
    "controller": ("Controller", [
        ".XXXXXXXX.",
        "XLLLLLLLLX",
        "XLKLLLLRLX",
        "XKKKLLRLRX",
        "XLKLLLLRLX",
        "XLLLXXLLLX",
        ".XXX..XXX.",
    ]),
    "note": ("Music note", [
        "....XXX..",
        "....XUUX.",
        "....XUXUX",
        "....XUX.X",
        "..XXXUX..",
        ".XUUUUX..",
        ".XUUUUX..",
        "..XXXX...",
    ]),
}


def icon_rows(emblem=None):
    c = app_icons.Canvas()
    app_icons.folder(c)
    c.outline()
    rows = [list(r) for r in c.rows()]
    if emblem in EMBLEMS:
        art = EMBLEMS[emblem][1]
        oy, ox = 16 - len(art), 16 - max(len(r) for r in art)
        for y, row in enumerate(art):
            for x, ch in enumerate(row):
                if ch != ".":
                    rows[oy + y][ox + x] = ch
    return ["".join(r) for r in rows]


def palette(color):
    _, front, shade = COLORS[color]
    return {**app_icons.PALETTE, "F": (*front, 255), "f": (*shade, 255)}


def icon_path(color, emblem=None):
    return OUT / (f"winux-{color}" + (f"-{emblem}" if emblem else "") + ".ico")


def build(color, emblem=None):
    """Write the .ico for this color + emblem (if it isn't there yet) and return its path."""
    p = icon_path(color, emblem)
    if not p.is_file():
        OUT.mkdir(parents=True, exist_ok=True)
        rows, pal = icon_rows(emblem), palette(color)
        p.write_bytes(px.ico([px.render(rows, pal, s) for s in (16, 3, 2, 1)]))   # 256, 48, 32, 16
    return p


def preview_png(path, scale=3, gap=6):
    """Every color in a row, then every emblem (for the panel)."""
    tiles = [(icon_rows(), palette(c)) for c in COLORS] + [(icon_rows(e), palette("yellow")) for e in EMBLEMS]
    imgs = [px.render(r, p, scale) for r, p in tiles]
    W = sum(w for w, _, _ in imgs) + gap * (len(imgs) - 1)
    H = max(h for _, h, _ in imgs)
    out = bytearray(W * H * 4)
    ox = 0
    for w, h, d in imgs:
        for y in range(h):
            out[(y * W + ox) * 4:(y * W + ox + w) * 4] = d[y * w * 4:(y + 1) * w * 4]
        ox += w + gap
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(px.png(W, H, bytes(out)))


# ---------------------------------------------------------------- desktop.ini

HIDDEN, SYSTEM, NORMAL = 0x2, 0x4, 0x80
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
shlwapi = ctypes.windll.shlwapi


def _read_ini(f):
    if not f.is_file():
        return []
    raw = f.read_bytes()
    for enc in ("utf-16",) if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "mbcs"):
        try:
            return raw.decode(enc).splitlines()
        except (UnicodeDecodeError, LookupError):
            pass
    return raw.decode("latin-1").splitlines()


def _icon_line(lines):
    """(index, value) of IconResource inside [.ShellClassInfo], or (None, None)."""
    section = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("["):
            section = s.lower()
        elif section == "[.shellclassinfo]" and s.lower().startswith("iconresource="):
            return i, s.split("=", 1)[1]
    return None, None


def _write_ini(folder, lines):
    f = folder / "desktop.ini"
    if f.exists():
        kernel32.SetFileAttributesW(str(f), NORMAL)     # hidden files can't be overwritten
    meaningful = [l for l in lines if l.strip() and l.strip().lower() != "[.shellclassinfo]"]
    if not meaningful:
        f.unlink(missing_ok=True)
        shlwapi.PathUnmakeSystemFolderW(str(folder))
    else:
        with open(f, "w", encoding="utf-16", newline="\r\n") as out:
            out.write("\n".join(lines) + "\n")
        kernel32.SetFileAttributesW(str(f), HIDDEN | SYSTEM)
        shlwapi.PathMakeSystemFolderW(str(folder))      # tells Explorer to read desktop.ini
    # SHCNE_UPDATEITEM + SHCNE_UPDATEDIR so Explorer redraws it now
    shell32.SHChangeNotify(0x00002000, 0x0005, str(folder), None)
    shell32.SHChangeNotify(0x00001000, 0x0005, str(folder.parent), None)


def _log():
    try:
        return json.loads(LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_log(log):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")


def current(folder):
    """(color, emblem) WinUx gave this folder, or (None, None)."""
    _, value = _icon_line(_read_ini(Path(folder) / "desktop.ini"))
    name = Path((value or "").rsplit(",", 1)[0]).stem
    if not name.startswith("winux-"):
        return None, None
    parts = name[6:].split("-")
    color = parts[0] if parts[0] in COLORS else None
    emblem = parts[1] if len(parts) > 1 and parts[1] in EMBLEMS else None
    return color, emblem


def set_folder(folder, color=None, emblem=None):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("That isn't a folder.")
    color = color if color in COLORS else "yellow"
    icon = build(color, emblem if emblem in EMBLEMS else None)
    lines = _read_ini(folder / "desktop.ini")
    i, old = _icon_line(lines)
    log = _log()
    key = str(folder)
    if key not in log:
        log[key] = {"original": old}           # so reset puts back whatever icon it had before
        _save_log(log)
    line = f"IconResource={icon},0"
    if i is not None:
        lines[i] = line
    else:
        at = next((n for n, l in enumerate(lines) if l.strip().lower() == "[.shellclassinfo]"), None)
        if at is None:
            lines = ["[.ShellClassInfo]", line] + ([""] + lines if lines else [])
        else:
            lines.insert(at + 1, line)
    _write_ini(folder, lines)


def reset_folder(folder):
    folder = Path(folder)
    log = _log()
    original = (log.pop(str(folder), None) or {}).get("original")
    _save_log(log)
    if not folder.is_dir():
        return
    lines = _read_ini(folder / "desktop.ini")
    i, value = _icon_line(lines)
    if i is None or not Path(value.rsplit(",", 1)[0]).stem.startswith("winux-"):
        return
    if original:
        lines[i] = f"IconResource={original}"
    else:
        del lines[i]
    _write_ini(folder, lines)


def reset_all():
    """Put every folder WinUx colored back. Returns how many."""
    folders = list(_log())
    for f in folders:
        try:
            reset_folder(f)
        except OSError:
            pass
    return len(folders)


def colored_count():
    return len(_log())


# ---------------------------------------------------------------- right-click menu

MENU = r"Software\Classes\Directory\shell"
COLOR_KEY, EMBLEM_KEY = "WinUxFolderColor", "WinUxFolderEmblem"


def _set(path, name, value, kind=winreg.REG_SZ):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def _delete_tree(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS) as k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _delete_tree(path + "\\" + sub)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def pythonw():
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return w if w.is_file() else exe


def menu_installed():
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU + "\\" + COLOR_KEY).Close()
        return True
    except OSError:
        return False


def install_menu():
    remove_menu()
    run = f'"{pythonw()}" "{Path(__file__).resolve()}" "%1"'

    def menu(key, label, icon, items):
        base = f"{MENU}\\{key}"
        _set(base, "MUIVerb", label)
        _set(base, "Icon", f"{icon},0")
        _set(base, "SubCommands", "")
        for n, (arg, name, item_icon, sep) in enumerate(items):
            item = f"{base}\\shell\\{n:02d}{arg.split('=')[-1]}"
            _set(item, "MUIVerb", name)
            if item_icon:
                _set(item, "Icon", f"{item_icon},0")
            if sep:
                _set(item, "CommandFlags", 0x20, winreg.REG_DWORD)   # line above it
            _set(item + "\\command", "", f"{run} {arg}")

    colors = [(f"color={c}", label, build(c), False) for c, (label, _, _) in COLORS.items()]
    colors.append(("reset", "Back to normal", None, True))
    menu(COLOR_KEY, "WinUx folder color", build("red", "heart"), colors)
    emblems = [(f"emblem={e}", label, build("yellow", e), False) for e, (label, _) in EMBLEMS.items()]
    emblems.append(("emblem=none", "No emblem", None, True))
    menu(EMBLEM_KEY, "WinUx folder emblem", build("yellow", "star"), emblems)


def remove_menu():
    _delete_tree(f"{MENU}\\{COLOR_KEY}")
    _delete_tree(f"{MENU}\\{EMBLEM_KEY}")


# ---------------------------------------------------------------- run from the right-click menu

def main(argv):
    if argv == ["--uninstall"]:          # used by uninstall.ps1
        remove_menu()
        reset_all()
        return
    if len(argv) < 2:
        return
    folder, what = argv[0], argv[1]
    color, emblem = current(folder)
    if what == "reset":
        reset_folder(folder)
    elif what.startswith("color="):
        set_folder(folder, what[6:], emblem)
    elif what.startswith("emblem="):
        e = what[7:]
        set_folder(folder, color or "yellow", None if e == "none" else e)
    try:   # tell WinUx (if it's running) so it can count this for achievements
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{os.environ.get('WINUX_PORT', '7777')}/event?e=folder", timeout=1)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:      # pythonw has no console: show what went wrong
        ctypes.windll.user32.MessageBoxW(None, f"WinUx couldn't change that folder:\n{e}", "WinUx", 0x10)
