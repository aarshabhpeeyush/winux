"""WinUx - the local helper that actually changes how Windows looks.

Runs a tiny web server on 127.0.0.1 only, serves the control panel in ui/,
and reads/writes the Windows "look" settings (dark mode, accent color,
wallpaper...). Uses only the Python standard library.
"""

import ctypes
import filecmp
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import webbrowser
import winreg
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _crash(kind, value, tb):
    """WinUx runs without a window (pythonw), so a crash would be invisible.
    Write it to winux-error.log and say so in a message box."""
    import traceback
    text = time.strftime("%Y-%m-%d %H:%M:%S ") + "".join(traceback.format_exception(kind, value, tb))
    log = Path(__file__).resolve().parent / "winux-error.log"
    for spot in (log, Path(os.environ.get("LOCALAPPDATA", ".")) / "WinUx" / "winux-error.log"):
        try:
            spot.parent.mkdir(parents=True, exist_ok=True)
            with open(spot, "a", encoding="utf-8") as f:
                f.write(text + "\n")
            log = spot
            break
        except OSError:
            continue
    try:
        ctypes.windll.user32.MessageBoxW(
            None, f"WinUx couldn't start:\n\n{value}\n\nThe details are in:\n{log}\n\n"
                  "Please send that file (or a screenshot of this) to the WinUx GitHub page.",
            "WinUx", 0x10)
    except Exception:
        pass


sys.excepthook = _crash

PORT = int(os.environ.get("WINUX_PORT", "7777"))   # another port only for testing
ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui"
WALLPAPERS = ROOT / "wallpapers"
ART_INBOX = ROOT / "art-inbox"
THEMES = ROOT / "themes"
BACKUPS = ROOT / "backups"
# Windows 11 is build 22000+. A few things (icon position, some mods) only exist there.
WIN11 = sys.getwindowsversion().build >= 22000
WIN_WALLPAPERS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Web" / "Wallpaper"
LIVE_WALLS = ROOT / "live-walls"
LIVELY_DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Lively Wallpaper"
LIVELY_LIB = LIVELY_DATA / "Library" / "wallpapers"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".gif"}
VERSION = "1.0.1"
TOKEN = secrets.token_hex(16)

for d in (WALLPAPERS, ART_INBOX, THEMES, BACKUPS, LIVE_WALLS):
    d.mkdir(exist_ok=True)

# ---------------------------------------------------------------- registry

HKCU = winreg.HKEY_CURRENT_USER
PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DWM = r"Software\Microsoft\Windows\DWM"
ACCENT = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
DESKTOP = r"Control Panel\Desktop"
ADVANCED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
SEARCH = r"Software\Microsoft\Windows\CurrentVersion\Search"

# Every value WinUx may touch. The backup snapshots exactly these.
TOUCHED = [
    (PERSONALIZE, "AppsUseLightTheme"),
    (PERSONALIZE, "SystemUsesLightTheme"),
    (PERSONALIZE, "EnableTransparency"),
    (PERSONALIZE, "ColorPrevalence"),
    (DWM, "AccentColor"),
    (DWM, "ColorizationColor"),
    (DWM, "ColorizationAfterglow"),
    (DWM, "ColorPrevalence"),
    (ACCENT, "AccentColorMenu"),
    (ACCENT, "StartColorMenu"),
    (ACCENT, "AccentPalette"),
    (DESKTOP, "WallPaper"),
    (DESKTOP, "WallpaperStyle"),
    (DESKTOP, "TileWallpaper"),
    (ADVANCED, "TaskbarAl"),
    (ADVANCED, "ShowTaskViewButton"),
    (SEARCH, "SearchboxTaskbarMode"),
]

# Cursors, sounds and desktop icons ("" = the key's default value).
CURSORS = r"Control Panel\Cursors"
CURSOR_ROLES = ["Arrow", "Hand", "IBeam", "Wait", "AppStarting"]
CURSOR_VALUES = [(CURSORS, r) for r in CURSOR_ROLES] + [(CURSORS, ""), (CURSORS, "Scheme Source")]

SOUND_EVENT_NAMES = [".Default", "SystemAsterisk", "SystemExclamation", "SystemHand", "SystemNotification",
                     "Notification.Default", "DeviceConnect", "DeviceDisconnect", "WindowsUAC", "MailBeep"]
SOUND_VALUES = [(rf"AppEvents\Schemes\Apps\.Default\{e}\.Current", "") for e in SOUND_EVENT_NAMES] \
    + [(r"AppEvents\Schemes", "")]

ICON_CLSID = r"Software\Microsoft\Windows\CurrentVersion\Explorer\CLSID"
DESKTOP_GUIDS = {
    "this-pc": "{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
    "user-folder": "{59031A47-3F72-44A7-89C5-5595FE6B30EE}",
    "network": "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}",
    "bin": "{645FF040-5081-101B-9F08-00AA002F954E}",
}
ICON_VALUES = [(rf"{ICON_CLSID}\{g}\DefaultIcon", "") for g in DESKTOP_GUIDS.values()] \
    + [(rf"{ICON_CLSID}\{DESKTOP_GUIDS['bin']}\DefaultIcon", n) for n in ("empty", "full")]

TOUCHED += CURSOR_VALUES + SOUND_VALUES + ICON_VALUES


def rget(path, name, default=None):
    try:
        with winreg.OpenKey(HKCU, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return default


def rset(path, name, value, kind=winreg.REG_DWORD):
    with winreg.CreateKeyEx(HKCU, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def rdelete(path, name):
    try:
        with winreg.OpenKey(HKCU, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


# ---------------------------------------------------------------- windows APIs

user32 = ctypes.WinDLL("user32", use_last_error=True)
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
SPI_SETDESKWALLPAPER = 0x0014


def broadcast(area=None):
    """Tell every open window 'settings changed, redraw yourself'."""
    result = wintypes.DWORD()
    user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, area,
                               SMTO_ABORTIFHUNG, 1000, ctypes.byref(result))


def set_wallpaper_file(path):
    user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(path), 0x01 | 0x02)


class APPBARDATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                ("uCallbackMessage", wintypes.UINT), ("uEdge", wintypes.UINT),
                ("rc", wintypes.RECT), ("lParam", wintypes.LPARAM)]


shell32 = ctypes.WinDLL("shell32")
shell32.SHAppBarMessage.argtypes = [wintypes.DWORD, ctypes.POINTER(APPBARDATA)]
shell32.SHAppBarMessage.restype = ctypes.c_size_t
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
ABM_GETSTATE, ABM_SETSTATE, ABS_AUTOHIDE, ABS_ALWAYSONTOP = 0x4, 0xA, 0x1, 0x2


def get_autohide():
    abd = APPBARDATA(cbSize=ctypes.sizeof(APPBARDATA))
    return bool(shell32.SHAppBarMessage(ABM_GETSTATE, ctypes.byref(abd)) & ABS_AUTOHIDE)


def set_autohide(on):
    """The official way to auto-hide the taskbar: applies instantly, no restart."""
    abd = APPBARDATA(cbSize=ctypes.sizeof(APPBARDATA))
    abd.hWnd = user32.FindWindowW("Shell_TrayWnd", None)
    abd.lParam = ABS_AUTOHIDE if on else ABS_ALWAYSONTOP
    shell32.SHAppBarMessage(ABM_SETSTATE, ctypes.byref(abd))


# ---------------------------------------------------------------- colors

def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r, g, b):
    return "#%02x%02x%02x" % (r, g, b)


def abgr(r, g, b, a=0xFF):
    return (a << 24) | (b << 16) | (g << 8) | r


def mix(rgb, target, amount):
    return tuple(round(c + (t - c) * amount) for c, t in zip(rgb, target))


def accent_palette(rgb):
    """The 8 shades Windows uses for Start, taskbar and buttons."""
    white, black = (255, 255, 255), (0, 0, 0)
    shades = [mix(rgb, white, 0.6), mix(rgb, white, 0.4), mix(rgb, white, 0.2), rgb,
              mix(rgb, black, 0.2), mix(rgb, black, 0.4), mix(rgb, black, 0.6),
              mix(rgb, black, 0.75)]
    return bytes(b for s in shades for b in (*s, 0)), shades


def write_accent(hexcolor):
    rgb = hex_to_rgb(hexcolor)
    palette, shades = accent_palette(rgb)
    r, g, b = rgb
    rset(ACCENT, "AccentPalette", palette, winreg.REG_BINARY)
    rset(ACCENT, "AccentColorMenu", abgr(*rgb))
    rset(ACCENT, "StartColorMenu", abgr(*shades[4]))
    rset(DWM, "AccentColor", abgr(*rgb))
    argb = (0xC4 << 24) | (r << 16) | (g << 8) | b
    rset(DWM, "ColorizationColor", argb)
    rset(DWM, "ColorizationAfterglow", argb)


# ---------------------------------------------------------------- wallpapers

STYLES = {"fill": ("10", "0"), "fit": ("6", "0"), "stretch": ("2", "0"),
          "tile": ("0", "1"), "center": ("0", "0"), "span": ("22", "0")}


def list_wallpapers():
    items = []
    for f in sorted(WALLPAPERS.iterdir(), key=lambda p: -p.stat().st_mtime):
        if f.suffix.lower() in IMAGE_EXTS:
            items.append({"id": "lib:" + f.name, "name": f.stem, "source": "yours"})
    for f in sorted(ART_INBOX.iterdir(), key=lambda p: -p.stat().st_mtime):
        if f.suffix.lower() in IMAGE_EXTS:
            items.append({"id": "art:" + f.name, "name": f.stem, "source": "art"})
    if WIN_WALLPAPERS.exists():
        for f in sorted(WIN_WALLPAPERS.rglob("*")):
            if f.suffix.lower() in IMAGE_EXTS:
                rel = f.relative_to(WIN_WALLPAPERS).as_posix()
                items.append({"id": "win:" + rel, "name": f.stem, "source": "windows"})
    return items


def wallpaper_path(wid):
    """Turn a wallpaper id into a real file, refusing anything outside our folders."""
    kind, _, rest = (wid or "").partition(":")
    base = {"lib": WALLPAPERS, "art": ART_INBOX, "win": WIN_WALLPAPERS,
            "backup": BACKUPS}.get(kind)
    if not base or not rest:
        return None
    p = (base / rest).resolve()
    if base.resolve() not in p.parents or not p.is_file():
        return None
    return p


def wallpaper_id_for(path):
    if not path:
        return None
    p = Path(path).resolve()
    for kind, base in (("lib", WALLPAPERS), ("art", ART_INBOX), ("win", WIN_WALLPAPERS)):
        if base.resolve() in p.parents:
            return kind + ":" + p.relative_to(base.resolve()).as_posix()
    return None


# ---------------------------------------------------------------- live wallpapers (Lively)

def lively_exe():
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        exe = Path(base) / "Lively Wallpaper" / "Lively.exe"
        if exe.is_file():
            return exe
    return None


def lively(*args):
    exe = lively_exe()
    if not exe:
        raise RuntimeError("Lively Wallpaper isn't installed.")
    running = subprocess.run(["tasklist", "/fi", "IMAGENAME eq Lively.exe", "/fo", "csv", "/nh"],
                             capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW).stdout
    if "Lively.exe" not in running:
        start_detached(str(exe))
        time.sleep(4)
    subprocess.run([str(exe), *args], capture_output=True, timeout=30,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def read_info(folder):
    try:
        return json.loads((folder / "LivelyInfo.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


EXTRAS = ("playable", "music")   # special labels shown on thumbnails


def live_extras(info):
    return [t for t in (info.get("Tags") or []) if t in EXTRAS]


def list_live():
    items = []
    for f in sorted(LIVE_WALLS.iterdir(), key=lambda p: p.name.lower()):
        if f.is_dir() and (info := read_info(f)):
            # WinUxName = the real name when Title is written in Wingdings symbols for Lively
            items.append({"id": "mine:" + f.name, "name": info.get("WinUxName") or info.get("Title") or f.name,
                          "source": "winux", "kind": "web",
                          "wingdings": "wingdings" in (info.get("Tags") or []),
                          "extras": live_extras(info)})
        elif f.suffix.lower() in VIDEO_EXTS:
            items.append({"id": "mine:" + f.name, "name": f.stem, "source": "yours",
                          "kind": "gif" if f.suffix.lower() == ".gif" else "video"})
    if LIVELY_LIB.exists():
        for f in sorted(LIVELY_LIB.iterdir()):
            if f.name.startswith(LIB_PREFIX):
                continue  # our own copies, already listed above
            info = read_info(f) if f.is_dir() else None
            if not info:
                continue
            items.append({"id": "lively:" + f.name, "name": info.get("Title") or f.name,
                          "source": "lively", "kind": "lively",
                          "thumb": bool(info.get("Thumbnail")), "preview": bool(info.get("Preview"))})
    return items


def live_path(lid):
    kind, _, rest = (lid or "").partition(":")
    base = {"mine": LIVE_WALLS, "lively": LIVELY_LIB}.get(kind)
    if not base or not rest or "/" in rest or "\\" in rest:
        return None
    p = (base / rest).resolve()
    if p.parent != base.resolve() or not p.exists():
        return None
    return p


def live_image(lid, which):
    """Thumbnail/preview image of a Lively library wallpaper."""
    p = live_path(lid)
    info = read_info(p) if p and p.is_dir() else None
    name = info and info.get("Preview" if which == "preview" else "Thumbnail")
    if not name:
        return None
    img = (p / name).resolve()
    return img if img.parent == p and img.is_file() else None


def current_live():
    try:
        layout = json.loads((LIVELY_DATA / "WallpaperLayout.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not layout:
        return None
    p = Path(layout[0].get("LivelyInfoPath", "")).resolve()
    if p.parent == LIVELY_LIB.resolve():
        if p.name.startswith(LIB_PREFIX):
            return "mine:" + p.name[len(LIB_PREFIX):]
        return "lively:" + p.name
    return "other"


# Lively only plays wallpapers inside its own library, so ours get copied in
# as "winux.<name>" folders right before they're set.
LIB_PREFIX = "winux."


def sync_to_lively(p):
    target = LIVELY_LIB / (LIB_PREFIX + p.name)
    if p.is_dir():
        shutil.copytree(p, target, dirs_exist_ok=True)
        return target
    target.mkdir(parents=True, exist_ok=True)
    if not (target / p.name).exists():
        shutil.copy2(p, target / p.name)
    info = {"AppVersion": "2.2.1.0", "Title": p.stem, "Thumbnail": None, "Preview": None,
            "Desc": "Added with WinUx.", "Author": "WinUx", "License": "", "Contact": "",
            "Type": 8 if p.suffix.lower() == ".gif" else 7,  # Lively: 7 = video, 8 = gif
            "FileName": p.name, "Arguments": None, "IsAbsolutePath": False,
            "Id": None, "Tags": ["winux"], "Version": 0}
    (target / "LivelyInfo.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return target


def set_live(lid):
    p = live_path(lid)
    if not p:
        raise RuntimeError("Couldn't find that live wallpaper.")
    if lid.startswith("mine:"):
        p = sync_to_lively(p)
    lively("setwp", "--file", str(p))


def lively_keyboard():
    """Does Lively pass the keyboard to wallpapers? (InputForward: 0 off, 1 mouse, 2 mouse+keyboard)"""
    try:
        return json.loads((LIVELY_DATA / "Settings.json").read_text(encoding="utf-8-sig")).get("InputForward") == 2
    except (OSError, ValueError):
        return False


def set_lively_keyboard(on):
    """Lively only reads its settings at start, so close it, change it, start it again."""
    exe = lively_exe()
    if not exe:
        raise RuntimeError("Lively Wallpaper isn't installed.")
    subprocess.run(["taskkill", "/im", "Lively.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(20):
        time.sleep(0.5)
        if "Lively.exe" not in subprocess.run(["tasklist", "/fi", "IMAGENAME eq Lively.exe", "/fo", "csv", "/nh"],
                                              capture_output=True, text=True,
                                              creationflags=subprocess.CREATE_NO_WINDOW).stdout:
            break
    else:
        subprocess.run(["taskkill", "/f", "/im", "Lively.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(1)
    f = LIVELY_DATA / "Settings.json"
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    data["InputForward"] = 2 if on else 1
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    start_detached(str(exe))   # it brings back the wallpaper that was playing


def stop_live():
    if lively_exe() and current_live():
        lively("closewp", "--monitor", "-1")


# ---------------------------------------------------------------- taskbar (TranslucentTB + Windows)

PACKAGES = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages"
TB_STYLES = ["normal", "clear", "blur", "acrylic", "opaque"]
SEARCH_MODES = {"hidden": 0, "icon": 1, "box": 2, "label": 3}   # "label" is Windows 11 only


def webview2_installed():
    """Lively's web wallpapers need Microsoft's WebView2 runtime (Windows 10 may not have it)."""
    guid = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}"),
                       (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
                       (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}")):
        try:
            with winreg.OpenKey(hive, path) as k:
                v = winreg.QueryValueEx(k, "pv")[0]
                if v and v != "0.0.0.0":
                    return True
        except OSError:
            pass
    return False


def ttb_family():
    for p in PACKAGES.glob("*CharlesMilette.TranslucentTB_*"):
        return p.name
    return None


def ttb_file():
    fam = ttb_family()
    return PACKAGES / fam / "RoamingState" / "settings.json" if fam else None


def ttb_default_look():
    return {"accent": "normal", "color": "#00000000", "show_peek": True,
            "show_line": False, "blur_radius": 9.0}


def ttb_read():
    f = ttb_file()
    try:
        return json.loads(f.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, AttributeError):
        data = {"$schema": "https://TranslucentTB.github.io/settings.schema.json",
                "desktop_appearance": ttb_default_look()}
        for key, accent in (("visible_window_appearance", "normal"),
                            ("maximized_window_appearance", "acrylic"),
                            ("start_opened_appearance", "normal"),
                            ("search_opened_appearance", "normal"),
                            ("task_view_opened_appearance", "normal"),
                            ("battery_saver_appearance", "opaque")):
            data[key] = {**ttb_default_look(), "enabled": key in (
                "start_opened_appearance", "search_opened_appearance",
                "task_view_opened_appearance", "battery_saver_appearance"), "accent": accent}
        data.update({"hide_tray": False, "disable_saving": False, "verbosity": "warn"})
        return data


def ttb_running():
    out = subprocess.run(["tasklist", "/fi", "IMAGENAME eq TranslucentTB.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return "TranslucentTB.exe" in out.stdout


def ttb_start():
    fam = ttb_family()
    if fam and not ttb_running():
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{fam}!TranslucentTB"])


def ttb_state():
    d = ttb_read()
    desk = d.get("desktop_appearance", {})
    color = str(desk.get("color", "#00000000"))
    mx = d.get("maximized_window_appearance", {})
    return {
        "tbStyle": desk.get("accent", "normal"),
        "tbColor": color[:7] if len(color) >= 7 else "#000000",
        "tbOpacity": round(int(color[7:9] or "00", 16) / 255 * 100) if len(color) == 9 else 0,
        "tbLine": bool(desk.get("show_line", False)),
        "tbMax": mx.get("accent", "acrylic") if mx.get("enabled") else "same",
    }


def ttb_write(s):
    d = ttb_read()
    desk = {**ttb_default_look(), **d.get("desktop_appearance", {})}
    cur = ttb_state()
    style = s.get("tbStyle", cur["tbStyle"])
    color = s.get("tbColor", cur["tbColor"])
    opacity = max(0, min(100, int(s.get("tbOpacity", cur["tbOpacity"]))))
    if style in TB_STYLES:
        desk["accent"] = style
    if re.fullmatch(r"#[0-9a-fA-F]{6}", str(color)):
        desk["color"] = color + "%02x" % round(opacity / 100 * 255)
    if "tbLine" in s:
        desk["show_line"] = bool(s["tbLine"])
    d["desktop_appearance"] = desk
    if "tbMax" in s:
        mx = {**ttb_default_look(), **d.get("maximized_window_appearance", {})}
        mx["enabled"] = s["tbMax"] != "same"
        if s["tbMax"] in TB_STYLES:
            mx["accent"] = s["tbMax"]
            mx["color"] = desk["color"]
        d["maximized_window_appearance"] = mx
    f = ttb_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=2), encoding="utf-8")
    ttb_start()


def taskbar_state():
    mode = rget(SEARCH, "SearchboxTaskbarMode", 2)
    return {
        "taskbarAlign": "left" if rget(ADVANCED, "TaskbarAl", 1) == 0 else "center",
        "searchMode": next((k for k, v in SEARCH_MODES.items() if v == mode), "box"),
        "taskView": rget(ADVANCED, "ShowTaskViewButton", 1) == 1,
        "autoHide": get_autohide(),
        "needsRestart": pending_restart,
    }


pending_restart = False  # icon position/search/Task View only show after a taskbar restart


def taskbar_write(s):
    global pending_restart
    before = taskbar_state()
    changed = False
    if WIN11 and s.get("taskbarAlign") in ("left", "center"):
        rset(ADVANCED, "TaskbarAl", 0 if s["taskbarAlign"] == "left" else 1)
        changed = True
    if s.get("searchMode") == "label" and not WIN11:
        s = {**s, "searchMode": "box"}
    if s.get("searchMode") in SEARCH_MODES:
        rset(SEARCH, "SearchboxTaskbarMode", SEARCH_MODES[s["searchMode"]])
        changed = True
    if "taskView" in s:
        rset(ADVANCED, "ShowTaskViewButton", 1 if s["taskView"] else 0)
        changed = True
    if "autoHide" in s:
        set_autohide(bool(s["autoHide"]))
    if changed:
        broadcast("TraySettings")
        after = taskbar_state()
        if any(before[k] != after[k] for k in ("taskbarAlign", "searchMode", "taskView")):
            pending_restart = True


# ---------------------------------------------------------------- widgets (Rainmeter)

RAINMETER = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Rainmeter" / "Rainmeter.exe"
RM_INI = Path(os.environ.get("APPDATA", "")) / "Rainmeter" / "Rainmeter.ini"
WIDGETS_SRC = ROOT / "widgets" / "WinUx"
SKIP_SKINS = {"WinUx", "@Backup", "@Vault"}

WINUX_WIDGETS = {
    "Clock": ("Clock", "Big pixel clock with the date."),
    "Stats": ("PC Status", "CPU, RAM and disk as HP bars."),
    "Music": ("Now Playing", "What Spotify is playing, with play/skip buttons."),
    "Dialog": ("Dialog Box", "Says something new every 10 minutes. Click it for more."),
    "Menu": ("Menu", "Launch Files, YouTube, Spotify, Discord and WinUx."),
    "Weather": ("Weather", "The weather, as told by a [[Big Shot]]. Click for a new pitch."),
    "Battery": ("Battery HP", "Your battery as an HP bar. Desktops have infinite HP."),
    "Calendar": ("Calendar", "This month, with today sitting on your soul."),
    "SavePoint": ("Save Point", "Click the star to save. LV = days your PC has been on."),
    "Shop": ("Tem Shop", "hOI!! Click an item to open that app."),
    "Timer": ("Focus Timer", "FIGHT your task for 25 minutes, then take a break."),
}
# Where each widget lands the first time on a 1920x1080 screen (you can drag them
# anywhere after). Other screen sizes get the same layout scaled to fit.
WIDGET_SPOTS = {"Clock": (40, 760), "Stats": (440, 790), "Music": (1480, 830),
                "Dialog": (860, 900), "Menu": (40, 420),
                "Battery": (300, 40), "SavePoint": (740, 40), "Weather": (1250, 40),
                "Shop": (300, 200), "Calendar": (1540, 250), "Timer": (1480, 600)}


def screen_size():
    """The main screen in real pixels (Rainmeter places skins in real pixels)."""
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
    w, h = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
    return (w, h) if w > 0 and h > 0 else (1920, 1080)


def widget_spot(name):
    """Where a WinUx widget goes on this screen, kept fully on screen."""
    spot = WIDGET_SPOTS.get(name)
    if not spot:
        return None
    sw, sh = screen_size()
    box = {"BoxW": 400, "BoxH": 150}
    try:
        for line in (WIDGETS_SRC / name / f"{name}.ini").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k in box and v.strip().isdigit():
                box[k] = int(v)
    except OSError:
        pass
    w, h = box["BoxW"] + 20, box["BoxH"] + 20          # plus the border and corner stars
    x = round(spot[0] * sw / 1920)
    y = round(spot[1] * sh / 1080)
    x = max(0, min(x, sw - w))
    y = max(0, min(y, sh - h - 48))                    # stay above the taskbar
    return x, y


def rm_read():
    """Rainmeter.ini as {section: {key: value}} (it's a UTF-16 file)."""
    sections, cur = {}, None
    try:
        text = RM_INI.read_text(encoding="utf-16")
    except (OSError, UnicodeError):
        return sections
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            cur = sections.setdefault(line[1:-1], {})
        elif cur is not None and "=" in line:
            k, _, v = line.partition("=")
            cur[k.strip()] = v.strip()
    return sections


def skins_path():
    p = rm_read().get("Rainmeter", {}).get("SkinPath")
    return Path(p) if p else Path.home() / "Documents" / "Rainmeter" / "Skins"


def skin_files(config):
    folder = skins_path() / config
    return sorted((f.name for f in folder.glob("*.ini")), key=str.lower) if folder.is_dir() else []


def active_configs():
    """{config: ini file} for every widget that's on right now."""
    out = {}
    for name, keys in rm_read().items():
        try:
            n = int(keys.get("Active", "0"))
        except ValueError:
            continue
        if n > 0:
            files = skin_files(name)
            out[name] = files[n - 1] if n <= len(files) else None
    return out


def rm_running():
    out = subprocess.run(["tasklist", "/fi", "IMAGENAME eq Rainmeter.exe", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return "Rainmeter.exe" in out.stdout


def rm_bang(*args):
    if not RAINMETER.is_file():
        raise RuntimeError("Rainmeter isn't installed.")
    if not rm_running():
        start_detached(str(RAINMETER))
        time.sleep(3)
    subprocess.run([str(RAINMETER), *args], capture_output=True, timeout=20,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def sync_widgets(accent=None):
    """Copy the WinUx widgets into Rainmeter's skins folder and set their colors."""
    target = skins_path() / "WinUx"
    for src in WIDGETS_SRC.rglob("*"):
        dst = target / src.relative_to(WIDGETS_SRC)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not (dst.exists() and filecmp.cmp(src, dst, shallow=False)):
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass  # in use by Rainmeter (fonts get locked); the old copy is fine
    accent = accent or get_state_accent()
    r, g, b = hex_to_rgb(accent)
    (target / "@Resources" / "Variables.inc").write_text(
        "[Variables]\n"
        "; Written by WinUx - change colors in the WinUx panel.\n"
        f"Accent={r},{g},{b}\nLine=255,255,255\nBg=0,0,0,235\nMuted=139,143,153\n"
        f"Soul=255,26,26\nWinUxDir={ROOT}\n", encoding="utf-8")


def get_state_accent():
    a = rget(DWM, "AccentColor", 0xFFD47800)
    return rgb_to_hex(a & 0xFF, (a >> 8) & 0xFF, (a >> 16) & 0xFF)


def set_widget(config, on, file=None):
    if config.startswith("WinUx\\"):
        sync_widgets()
    if on:
        files = skin_files(config)
        file = file if file in files else (files[0] if files else None)
        if not file:
            raise RuntimeError(f"Couldn't find the widget {config}.")
        keys = rm_read().get(config, {})
        first_time = keys.get("WindowX", "0") == "0" and keys.get("WindowY", "0") == "0"
        was_on = config in active_configs()
        rm_bang("!ActivateConfig", config, file)
        if was_on:
            rm_bang("!Refresh", config)  # already showing: reload it so new files take effect
        time.sleep(1)
        if config not in active_configs():
            # Rainmeter only knows skins that existed when it started. Make it look again.
            rm_bang("!RefreshApp")
            time.sleep(5)
            rm_bang("!ActivateConfig", config, file)
        spot = widget_spot(config.split("\\", 1)[-1]) if config.startswith("WinUx\\") else None
        if first_time and spot:
            rm_bang("!Move", str(spot[0]), str(spot[1]), config)
    else:
        rm_bang("!DeactivateConfig", config)


def list_widgets():
    active = active_configs()
    mine = [{"config": "WinUx\\" + k, "name": n, "what": w, "active": ("WinUx\\" + k) in active}
            for k, (n, w) in WINUX_WIDGETS.items()]
    yours = []
    root = skins_path()
    if root.is_dir():
        for folder in sorted(root.rglob("*")):
            if not folder.is_dir():
                continue
            rel = folder.relative_to(root)
            if rel.parts[0] in SKIP_SKINS or "@Resources" in rel.parts or not any(folder.glob("*.ini")):
                continue
            config = "\\".join(rel.parts)
            yours.append({"config": config, "name": config, "active": config in active,
                          "files": skin_files(config), "file": active.get(config)})
    return {"installed": RAINMETER.is_file(), "mine": mine, "yours": yours}


def apply_widget_set(names):
    """Themes say which WinUx widgets should be on; the rest of WinUx's go off.
    Your own (non-WinUx) widgets are never touched by themes."""
    active = active_configs()
    for key in WINUX_WIDGETS:
        config = "WinUx\\" + key
        want = key in names
        if want != (config in active):
            set_widget(config, want)


# ---------------------------------------------------------------- cursors, sounds, desktop icons

import assets  # noqa: E402  (WinUx's own pixel art + chiptunes)
import app_icons  # noqa: E402  (pixel-art app logos)

GENERATED = ROOT / "generated"
SPI_SETCURSORS = 0x0057
CURSOR_SCHEMES = {"pixel": "WinUx Pixel", "pixel-accent": "WinUx Pixel Accent", "soul": "WinUx Soul"}


def restore_values(values):
    """Put a group of settings back exactly how the original backup had them."""
    data = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    saved = {(v["path"], v["name"]): v for v in data["values"]}
    for key in values:
        v = saved.get(key)
        if not v:
            continue
        if v.get("missing"):
            rdelete(v["path"], v["name"])
        else:
            val = bytes.fromhex(v["value"]) if v["kind"] == winreg.REG_BINARY else v["value"]
            rset(v["path"], v["name"], val, v["kind"])


def reload_cursors():
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0x01 | 0x02)


def refresh_icons():
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # "icons changed, redraw"


def cursors_state():
    arrow = str(rget(CURSORS, "Arrow", "") or "").lower()
    for scheme in CURSOR_SCHEMES:
        if f"\\generated\\cursors\\{scheme}\\" in arrow:
            return scheme
    return "default"


def set_cursors(scheme, accent=None):
    if scheme in CURSOR_SCHEMES:
        files = assets.build_cursors(scheme, accent or get_state_accent())
        for role, path in files.items():
            rset(CURSORS, role, path, winreg.REG_EXPAND_SZ)
        rset(CURSORS, "", CURSOR_SCHEMES[scheme], winreg.REG_SZ)
        rset(CURSORS, "Scheme Source", 1)
    else:
        restore_values(CURSOR_VALUES)
    reload_cursors()


def sounds_state():
    first = str(rget(SOUND_VALUES[0][0], "", "") or "")
    if "\\generated\\sounds\\" in first.lower():
        return "chiptune"
    if all(not rget(p, "", "") for p, _ in SOUND_VALUES[:-1]):
        return "silent"
    return "default"


def set_sounds(scheme):
    if scheme == "chiptune":
        files = assets.build_sounds()
        for event in SOUND_EVENT_NAMES:
            rset(rf"AppEvents\Schemes\Apps\.Default\{event}\.Current", "", files[event], winreg.REG_EXPAND_SZ)
        rset(r"AppEvents\Schemes", "", ".Current", winreg.REG_SZ)
    elif scheme == "silent":
        for event in SOUND_EVENT_NAMES:
            rset(rf"AppEvents\Schemes\Apps\.Default\{event}\.Current", "", "", winreg.REG_EXPAND_SZ)
        rset(r"AppEvents\Schemes", "", ".None", winreg.REG_SZ)
    else:
        restore_values(SOUND_VALUES)


def icons_state():
    v = str(rget(rf"{ICON_CLSID}\{DESKTOP_GUIDS['this-pc']}\DefaultIcon", "", "") or "")
    return "pixel" if "\\generated\\icons\\" in v.lower() else "default"


def set_icons(scheme):
    if scheme == "pixel":
        files = assets.build_icons()
        for name in ("this-pc", "user-folder", "network"):
            rset(rf"{ICON_CLSID}\{DESKTOP_GUIDS[name]}\DefaultIcon", "", files[name] + ",0", winreg.REG_EXPAND_SZ)
        bin_key = rf"{ICON_CLSID}\{DESKTOP_GUIDS['bin']}\DefaultIcon"
        rset(bin_key, "empty", files["bin-empty"] + ",0", winreg.REG_EXPAND_SZ)
        rset(bin_key, "full", files["bin-full"] + ",0", winreg.REG_EXPAND_SZ)
        rset(bin_key, "", files["bin-empty"] + ",0", winreg.REG_EXPAND_SZ)
    else:
        restore_values(ICON_VALUES)
    refresh_icons()


# ---------------------------------------------------------------- app icons

# Pixel-art logos for app shortcuts on the desktop, the Start menu and the taskbar.
# Shortcuts for everyone (Public Desktop, the shared Start menu) and the folder icon
# need admin, so those go in one Windows permission prompt.
SHORTCUT_TOOL = ROOT / "tools" / "shortcuts.ps1"
APP_ICONS_BACKUP = BACKUPS / "app-icons.json"
ADMIN_PLACES = ("public-desktop", "public-start")
SHELL_ICONS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"


STYLER = r"SOFTWARE\Windhawk\Engine\Mods\windows-11-taskbar-styler"
STYLER_MARK = "// WinUx"            # first style of each entry WinUx adds (the mod skips // lines)
START_BTN = ("Taskbar.ExperienceToggleButton#LaunchListButton[AutomationProperties.AutomationId=StartButton]"
             " > Taskbar.TaskListButtonPanel")


def styler_installed():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, STYLER) as k:
            return winreg.QueryValueEx(k, "Disabled")[0] == 0
    except OSError:
        return False


def styler_entries():
    """Taskbar Styler's style list as [(index, target, [styles])]."""
    out = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, STYLER + r"\Settings") as k:
            i = 0
            while True:
                try:
                    target = winreg.QueryValueEx(k, f"controlStyles[{i}].target")[0]
                except OSError:
                    break
                if not target:
                    break
                styles, j = [], 0
                while True:
                    try:
                        st = winreg.QueryValueEx(k, f"controlStyles[{i}].styles[{j}]")[0]
                    except OSError:
                        break
                    if not st:
                        break
                    styles.append(st)
                    j += 1
                out.append((i, target, styles))
                i += 1
    except OSError:
        pass
    return out


def styler_plan(on):
    """What to write so the Start button and search show WinUx icons (on) or not (off).
    WinUx's entries are found by their first style, STYLER_MARK."""
    if not WIN11 or not styler_installed():
        return None
    existing = styler_entries()
    mine = [e for e in existing if e[2][:1] == [STYLER_MARK]]
    win = Path(app_icons.taskbar_png("windows", app_icons.OUT / "taskbar-windows.png")).as_uri()
    search = Path(app_icons.taskbar_png("search", app_icons.OUT / "taskbar-search.png")).as_uri()
    # the wide search box keeps its icon on the left; the icon-only button centers it
    align = "Left" if rget(SEARCH, "SearchboxTaskbarMode", 2) == 2 else "Center"
    wanted = [
        (f"{START_BTN} > Grid > Microsoft.UI.Xaml.Controls.AnimatedVisualPlayer#Icon, "
         f"{START_BTN} > Microsoft.UI.Xaml.Controls.AnimatedVisualPlayer#Icon",
         [STYLER_MARK, "Visibility=Collapsed"]),
        (f"{START_BTN} > Grid > Border#BackgroundElement, {START_BTN} > Border#BackgroundElement",
         [STYLER_MARK, f'Background:=<ImageBrush Stretch="Uniform" ImageSource="{win}" />']),
        # the search icon (works for both the search box and the icon-only search button)
        ("SearchUx.SearchUI.SearchButtonRootGrid#SearchBoxButtonRootPanel > Grid > "
         "Microsoft.UI.Xaml.Controls.AnimatedVisualPlayer, "
         "SearchUx.SearchUI.SearchButtonRootGrid#SearchBoxButtonRootPanel > "
         "Microsoft.UI.Xaml.Controls.AnimatedVisualPlayer",
         [STYLER_MARK, "Visibility=Collapsed"]),
        ("SearchUx.SearchUI.SearchButtonRootGrid#SearchBoxButtonRootPanel > Grid > Border#BackgroundElement, "
         "SearchUx.SearchUI.SearchButtonRootGrid#SearchBoxButtonRootPanel > Border#BackgroundElement",
         [STYLER_MARK, f'Background:=<ImageBrush Stretch="Uniform" AlignmentX="{align}" ImageSource="{search}" />']),
    ]
    # reuse WinUx's old slots, add new ones after everything else
    slots = [e[0] for e in mine] + list(range(len(existing), len(existing) + len(wanted)))
    plan = []
    for (target, styles), i in zip(wanted, slots):
        plan.append({"index": i, "target": target if on else "//" + target.lstrip("/"), "styles": styles})
    if not on:
        plan = [{"index": e[0], "target": "//" + e[1].lstrip("/"), "styles": e[2]} for e in mine]
    return plan


def which_app(sc):
    """Which app a shortcut opens (or None). sc = one item from shortcuts.ps1 list."""
    exe = Path(sc.get("target") or "").name.lower()
    name = (sc.get("name") or "").lower()
    url = (sc.get("url") or "").lower()
    args = (sc.get("args") or "").lower()
    if exe == "chrome.exe":
        return "chrome"
    if name == "file explorer" or (exe == "explorer.exe" and not args):
        return "files"
    if exe == "claude.exe" or name == "claude":
        return "claude"
    if exe == "vlc.exe":
        return "vlc"
    if exe == "discord.exe" or (exe == "update.exe" and "discord" in args):
        return "discord"
    if exe == "spotify.exe":
        return "spotify"
    if exe.startswith("robloxplayer") or name in ("roblox", "roblox player"):
        return "roblox"
    if exe == "deltarune.exe" or "rungameid/1671210" in url or "deltarune" in name:
        return "deltarune"
    if exe == "undertale.exe" or "rungameid/391540" in url or "undertale" in name:
        return "undertale"
    if exe == "steam.exe":
        return "steam"
    if exe == "lively.exe":
        return "lively"
    return None


def run_tool(mode, data=None, admin=False):
    """Run shortcuts.ps1. Returns its output (list for "list", log lines otherwise)."""
    tmp = BACKUPS / "tmp"
    tmp.mkdir(exist_ok=True)
    out = tmp / f"{mode}-out.json"
    inp = tmp / f"{mode}-in.json"
    out.unlink(missing_ok=True)
    args = ["-Mode", mode, "-Out", str(out)]
    if data is not None:
        inp.write_text(json.dumps(data), encoding="utf-8")
        args += ["-In", str(inp)]
    base = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"]
    if admin:
        # One UAC prompt. Quotes keep paths with spaces in one piece.
        arglist = ",".join("'\"{}\"'".format(a) if " " in a else f"'{a}'"
                           for a in ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SHORTCUT_TOOL), *args])
        cmd = base + ["-WindowStyle", "Hidden", "-Command",
                      f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList {arglist}"]
    else:
        cmd = base + ["-File", str(SHORTCUT_TOOL), *args]
    subprocess.run(cmd, capture_output=True, timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
    if not out.is_file():
        return None
    text = out.read_text(encoding="utf-8-sig")
    return json.loads(text) if mode == "list" else text.splitlines()


def app_icons_backup():
    try:
        return json.loads(APP_ICONS_BACKUP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pack": "default", "shortcuts": {}, "folder": None}


def app_icons_state():
    return app_icons_backup().get("pack", "default")


def set_app_icons(pack):
    """pack "pixel" = WinUx logos, "default" = put every original icon back."""
    back = app_icons_backup()
    shortcuts = run_tool("list") or []
    user, admin = [], []
    folder = None
    if pack == "pixel":
        files = app_icons.build_app_icons()
        for sc in shortcuts:
            app = which_app(sc)
            if not app:
                continue
            back["shortcuts"].setdefault(sc["path"], sc.get("icon") or "")   # remember the original once
            (admin if sc["place"] in ADMIN_PLACES else user).append({"path": sc["path"], "icon": files[app]})
        if "folder" not in back or back.get("folderSaved") is not True:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SHELL_ICONS) as k:
                    back["folder"] = winreg.QueryValueEx(k, "3")[0]
            except OSError:
                back["folder"] = None
            back["folderSaved"] = True
        folder = files["folder"]
    else:
        places = {sc["path"]: sc["place"] for sc in shortcuts}
        for path, icon in back["shortcuts"].items():
            if path in places:
                (admin if places[path] in ADMIN_PLACES else user).append({"path": path, "icon": icon})
        folder = (back.get("folder") or "").rsplit(",", 1)[0] if back.get("folderSaved") else None
    APP_ICONS_BACKUP.write_text(json.dumps(back, indent=2), encoding="utf-8")

    log = run_tool("set", {"shortcuts": user}) or [] if user else []
    admin_ok = True
    styler = styler_plan(pack == "pixel")
    folder_done = back.get("folderApplied") == (folder or "")
    if admin or not folder_done or styler:
        res = run_tool("admin", {"shortcuts": admin, "folder": folder or "", "styler": styler or []}, admin=True)
        admin_ok = res is not None
        log += res or []
    if pack == "default" and admin_ok:
        back = {"pack": "default", "shortcuts": {}, "folder": None}
    else:
        back["pack"] = pack
        if admin_ok:
            back["folderApplied"] = folder or ""
    APP_ICONS_BACKUP.write_text(json.dumps(back, indent=2), encoding="utf-8")
    refresh_icons()
    try:
        subprocess.run(["ie4uinit.exe", "-show"], timeout=20,   # rebuild Windows' icon cache
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        pass
    changed = sum(1 for line in log if line.startswith("ok "))
    return {"changed": changed, "admin": admin_ok}


# ---------------------------------------------------------------- start with Windows

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
STARTUP_FOLDER = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
TTB_TASK = (r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel"
            r"\SystemAppData\{fam}\TranslucentTB")


def base_pythonw():
    """pythonw.exe from the real Python install (not a borrowed virtual env)."""
    p = Path(sys.base_prefix) / "pythonw.exe"
    return p if p.is_file() else Path(sys.executable).with_name("pythonw.exe")


def approved(kind, name):
    """Task Manager's on/off switch for a startup entry (missing = on)."""
    v = rget(rf"{APPROVED}\{kind}", name)
    return not (isinstance(v, bytes) and v[:1] == b"\x03")


def set_approved(kind, name, on):
    rset(rf"{APPROVED}\{kind}", name, bytes([2 if on else 3]) + bytes(11), winreg.REG_BINARY)


def startup_state():
    items = {}
    cmd = rget(RUN, "WinUx")
    items["winux"] = {"name": "WinUx", "what": "This panel, quietly in the background.",
                      "installed": True, "on": bool(cmd) and approved("Run", "WinUx")}
    items["lively"] = {"name": "Lively", "what": "Live wallpapers.", "installed": lively_exe() is not None,
                       "on": bool(rget(RUN, "Lively")) and approved("Run", "Lively")}
    rm_link = STARTUP_FOLDER / "Rainmeter.lnk"
    items["rainmeter"] = {"name": "Rainmeter", "what": "Desktop widgets.", "installed": RAINMETER.is_file(),
                          "on": rm_link.is_file() and approved("StartupFolder", "Rainmeter.lnk")}
    fam = ttb_family()
    items["ttb"] = {"name": "TranslucentTB", "what": "Taskbar looks.", "installed": fam is not None,
                    "on": bool(fam) and rget(TTB_TASK.format(fam=fam), "State", 0) in (2, 4)}
    items["windhawk"] = {"name": "Windhawk", "what": "Mods. Always starts (it's a Windows service).",
                         "installed": WINDHAWK.is_file(), "on": WINDHAWK.is_file(), "fixed": True}
    return items


def set_startup(key, on):
    if key == "winux":
        if on:
            rset(RUN, "WinUx", f'"{base_pythonw()}" "{ROOT / "server.py"}" --no-browser', winreg.REG_SZ)
        else:
            rdelete(RUN, "WinUx")
        set_approved("Run", "WinUx", on)
    elif key == "lively":
        if on and not rget(RUN, "Lively") and lively_exe():
            rset(RUN, "Lively", f'"{lively_exe()}"', winreg.REG_SZ)
        set_approved("Run", "Lively", on)
    elif key == "rainmeter":
        set_approved("StartupFolder", "Rainmeter.lnk", on)
    elif key == "ttb" and ttb_family():
        rset(TTB_TASK.format(fam=ttb_family()), "State", 2 if on else 1)
    else:
        raise RuntimeError("That one can't be switched here.")


# ---------------------------------------------------------------- Windhawk mods

WINDHAWK = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Windhawk" / "windhawk.exe"

# Hand-picked mods. Windhawk only installs mods from inside its own app,
# so WinUx shows these and opens Windhawk for you.
MODS = [
    {"id": "windows-11-taskbar-styler", "win11": True, "name": "Windows 11 Taskbar Styler",
     "what": "Whole new taskbar looks. Try the DockLike, Bubbles, Squircle or WinXP themes."},
    {"id": "windows-11-start-menu-styler", "win11": True, "name": "Windows 11 Start Menu Styler",
     "what": "Restyle Start. Try SideBySide, NoRecommendedSection or RosePine."},
    {"id": "taskbar-icon-size", "name": "Taskbar height and icon size",
     "what": "Make the taskbar thinner or chunkier, with smaller or bigger icons."},
    {"id": "taskbar-clock-customization", "name": "Taskbar Clock Customization",
     "what": "Show seconds, the weekday, or your own text next to the clock."},
    {"id": "taskbar-labels", "win11": True, "name": "Taskbar Labels for Windows 11",
     "what": "Show app names next to taskbar icons."},
    {"id": "taskbar-on-top", "win11": True, "name": "Taskbar on top for Windows 11",
     "what": "Move the taskbar to the top of the screen, Linux-style."},
    {"id": "taskbar-vertical", "win11": True, "name": "Vertical Taskbar for Windows 11",
     "what": "Put the taskbar on the left or right side, standing up."},
    {"id": "taskbar-auto-hide-when-maximized", "name": "Taskbar auto-hide when maximized",
     "what": "Taskbar hides only when a window is full size."},
    {"id": "windows-11-file-explorer-styler", "win11": True, "name": "Windows 11 File Explorer Styler",
     "what": "Restyle File Explorer to match your theme."},
    {"id": "windows-11-notification-center-styler", "win11": True, "name": "Notification Center Styler",
     "what": "Restyle the notifications and calendar pop-up."},
]


def windhawk_mods():
    """Which mods are installed (Windhawk keeps them in a read-only-for-us registry key)."""
    installed = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Windhawk\Engine\Mods") as k:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(k, name) as mk:
                        disabled = winreg.QueryValueEx(mk, "Disabled")[0] == 1
                except OSError:
                    disabled = False
                installed[name] = not disabled
    except OSError:
        pass
    return [{**m, "installed": m["id"] in installed, "enabled": installed.get(m["id"], False)}
            for m in MODS if WIN11 or not m.get("win11")]


def open_windhawk():
    if not WINDHAWK.is_file():
        raise RuntimeError("Windhawk isn't installed.")
    subprocess.Popen([str(WINDHAWK)])


def safe_name(name, fallback="image"):
    stem = re.sub(r"[^A-Za-z0-9 _-]+", "", Path(name).stem).strip()[:60] or fallback
    ext = Path(name).suffix.lower()
    return stem, ext


# ---------------------------------------------------------------- state

def get_state():
    accent = rget(DWM, "AccentColor", 0xFFD47800)
    style_val = (str(rget(DESKTOP, "WallpaperStyle", "10")),
                 str(rget(DESKTOP, "TileWallpaper", "0")))
    style = next((k for k, v in STYLES.items() if v == style_val), "fill")
    wp = rget(DESKTOP, "WallPaper", "")
    return {
        "version": VERSION,
        "win11": WIN11,
        "webview2": webview2_installed(),
        "appsDark": rget(PERSONALIZE, "AppsUseLightTheme", 1) == 0,
        "systemDark": rget(PERSONALIZE, "SystemUsesLightTheme", 1) == 0,
        "transparency": rget(PERSONALIZE, "EnableTransparency", 1) == 1,
        "accent": rgb_to_hex(accent & 0xFF, (accent >> 8) & 0xFF, (accent >> 16) & 0xFF),
        "accentOnTaskbar": rget(PERSONALIZE, "ColorPrevalence", 0) == 1,
        "accentOnTitlebars": rget(DWM, "ColorPrevalence", 0) == 1,
        "wallpaper": wallpaper_id_for(wp),
        "wallpaperPath": wp,
        "wallpaperStyle": style,
        "lively": lively_exe() is not None,
        "live": current_live(),
        "liveKeyboard": lively_keyboard(),
        "ttb": ttb_family() is not None,
        "windhawk": WINDHAWK.is_file(),
        **ttb_state(),
        **taskbar_state(),
        "cursors": cursors_state(),
        "sounds": sounds_state(),
        "icons": icons_state(),
        "appIcons": app_icons_state(),
        "rainmeter": RAINMETER.is_file(),
        "widgets": sorted(c.split("\\", 1)[1] for c in active_configs() if c.startswith("WinUx\\")),
    }


def apply_settings(s):
    """Apply any subset of the state keys. Unknown keys are ignored."""
    if "appsDark" in s:
        rset(PERSONALIZE, "AppsUseLightTheme", 0 if s["appsDark"] else 1)
    if "systemDark" in s:
        rset(PERSONALIZE, "SystemUsesLightTheme", 0 if s["systemDark"] else 1)
    if "transparency" in s:
        rset(PERSONALIZE, "EnableTransparency", 1 if s["transparency"] else 0)
    if "accent" in s and re.fullmatch(r"#[0-9a-fA-F]{6}", str(s["accent"])):
        write_accent(s["accent"])
    if "accentOnTaskbar" in s:
        rset(PERSONALIZE, "ColorPrevalence", 1 if s["accentOnTaskbar"] else 0)
    if "accentOnTitlebars" in s:
        rset(DWM, "ColorPrevalence", 1 if s["accentOnTitlebars"] else 0)

    if "wallpaperStyle" in s and s["wallpaperStyle"] in STYLES:
        style, tile = STYLES[s["wallpaperStyle"]]
        rset(DESKTOP, "WallpaperStyle", style, winreg.REG_SZ)
        rset(DESKTOP, "TileWallpaper", tile, winreg.REG_SZ)
    if ttb_family() and any(k in s for k in ("tbStyle", "tbColor", "tbOpacity", "tbLine", "tbMax")):
        ttb_write(s)
    taskbar_write(s)

    if "accent" in s:
        assets.build_previews(s["accent"])
    if s.get("cursors") in ("default", *CURSOR_SCHEMES):
        set_cursors(s["cursors"], s.get("accent"))
    elif "accent" in s and cursors_state() == "pixel-accent":
        set_cursors("pixel-accent", s["accent"])   # accent cursors follow your accent color
    if s.get("sounds") in ("default", "chiptune", "silent"):
        set_sounds(s["sounds"])
    if s.get("icons") in ("default", "pixel"):
        set_icons(s["icons"])
    app_result = None
    if s.get("appIcons") in ("default", "pixel"):
        app_result = set_app_icons(s["appIcons"])

    if RAINMETER.is_file():
        if isinstance(s.get("widgets"), list):
            apply_widget_set(s["widgets"])
        if "accent" in s and (skins_path() / "WinUx").is_dir():
            # Widgets follow your accent color.
            sync_widgets(s["accent"])
            if any(c.startswith("WinUx\\") for c in active_configs()):
                rm_bang("!RefreshGroup", "WinUx")

    if "live" in s:
        # A live wallpaper id starts it; null stops it.
        if s["live"]:
            if lively_exe():
                set_live(s["live"])
        else:
            stop_live()
    elif s.get("wallpaper"):
        # A picture is hidden behind a live wallpaper, so stop the live one.
        stop_live()

    if s.get("wallpaper"):
        p = wallpaper_path(s["wallpaper"])
        if p:
            set_wallpaper_file(p)
    elif "wallpaperStyle" in s:
        # Style changes only show once the wallpaper is set again.
        current = rget(DESKTOP, "WallPaper", "")
        if current:
            set_wallpaper_file(current)

    # Telling every window to redraw is slow, so only do it when colors changed.
    if any(k in s for k in ("appsDark", "systemDark", "transparency", "accent",
                            "accentOnTaskbar", "accentOnTitlebars")):
        broadcast("ImmersiveColorSet")
        broadcast("WindowsThemeElement")
        broadcast(None)
    state = get_state()
    if "live" in s and state["lively"]:
        state["live"] = s["live"] or None  # Lively saves its layout a moment later
    if app_result:
        state["appIconsResult"] = app_result
    return state


# ---------------------------------------------------------------- backup

ORIGINAL = BACKUPS / "original.json"


def snapshot_value(path, name):
    try:
        with winreg.OpenKey(HKCU, path) as k:
            val, kind = winreg.QueryValueEx(k, name)
        if isinstance(val, bytes):
            val = val.hex()
        return {"path": path, "name": name, "kind": kind, "value": val}
    except OSError:
        return {"path": path, "name": name, "missing": True}


def snapshot():
    values = [snapshot_value(path, name) for path, name in TOUCHED]
    data = {"saved": time.strftime("%Y-%m-%d %H:%M"), "values": values,
            "autoHide": get_autohide(), "rainmeterActive": active_configs()}
    wp = rget(DESKTOP, "WallPaper", "")
    if wp and Path(wp).is_file():
        # Keep a copy: some wallpapers (like the Photos app's) get deleted later.
        copy = BACKUPS / ("original-wallpaper" + Path(wp).suffix.lower())
        shutil.copy2(wp, copy)
        data["wallpaperCopy"] = copy.name
        data["wallpaperOriginal"] = wp
    return data


def ensure_original_backup():
    if not ORIGINAL.exists():
        ORIGINAL.write_text(json.dumps(snapshot(), indent=2), encoding="utf-8")
        return
    # Newer WinUx versions touch more settings: back those up too, before first use.
    data = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    have = {(v["path"], v["name"]) for v in data["values"]}
    extra = [snapshot_value(p, n) for p, n in TOUCHED if (p, n) not in have]
    if extra or "autoHide" not in data or "rainmeterActive" not in data:
        data["values"] += extra
        data.setdefault("autoHide", get_autohide())
        data.setdefault("rainmeterActive", active_configs())
        ORIGINAL.write_text(json.dumps(data, indent=2), encoding="utf-8")


def restore_original():
    global pending_restart
    data = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    tb_before = taskbar_state()
    stop_live()
    for v in data["values"]:
        if v.get("missing"):
            rdelete(v["path"], v["name"])
            continue
        val = bytes.fromhex(v["value"]) if v["kind"] == winreg.REG_BINARY else v["value"]
        rset(v["path"], v["name"], val, v["kind"])
    wp = data.get("wallpaperOriginal")
    if wp and Path(wp).is_file():
        set_wallpaper_file(wp)
    elif data.get("wallpaperCopy"):
        set_wallpaper_file(BACKUPS / data["wallpaperCopy"])
    set_autohide(data.get("autoHide", False))
    reload_cursors()
    refresh_icons()
    if app_icons_state() != "default":
        set_app_icons("default")
    if RAINMETER.is_file() and "rainmeterActive" in data:
        # Put the widgets back exactly how they were: same ones on, same ones off.
        was, now = data["rainmeterActive"], active_configs()
        for config in now:
            if config not in was:
                set_widget(config, False)
        for config, file in was.items():
            if config not in now and skin_files(config):
                set_widget(config, True, file)
    tb_after = taskbar_state()
    if any(tb_before[k] != tb_after[k] for k in ("taskbarAlign", "searchMode", "taskView")):
        pending_restart = True
    if ttb_family():
        # Windows had no TranslucentTB before, so put it back to the plain look.
        ttb_write({"tbStyle": "normal", "tbColor": "#000000", "tbOpacity": 0,
                   "tbLine": False, "tbMax": "same"})
    broadcast("TraySettings")
    broadcast("ImmersiveColorSet")
    broadcast("WindowsThemeElement")
    broadcast(None)
    return get_state()


def restart_explorer():
    """Some taskbar colors only fully update after Explorer restarts."""
    global pending_restart
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    pending_restart = False
    # Windows brings the taskbar back by itself (AutoRestartShell). Give it time.
    for _ in range(8):
        time.sleep(0.5)
        if user32.FindWindowW("Shell_TrayWnd", None):
            return
    start_detached(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "explorer.exe"))


def start_detached(exe):
    """Start a program through WMI so it is NOT a child of WinUx.
    (A child gets closed together with WinUx - that once took the taskbar with it.)"""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
                    f"-Arguments @{{CommandLine='\"{exe}\"'}}"],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


# ---------------------------------------------------------------- themes

PRESETS = [
    {"name": "Dark World", "blurb": "Black, white and that yellow glow.",
     "settings": {"cursors": "pixel", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": False,
                  "accent": "#ffe600", "accentOnTaskbar": False, "accentOnTitlebars": False,
                  "live": "mine:dark-world", "widgets": ["Clock", "Dialog", "Menu"],
                  "tbStyle": "clear", "tbColor": "#000000", "tbOpacity": 0, "tbMax": "opaque"}},
    {"name": "Soul Red", "blurb": "Determination. Red title bars.",
     "settings": {"cursors": "soul", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#d4141e", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:soul-red",
                  "tbStyle": "acrylic", "tbColor": "#d4141e", "tbOpacity": 25, "tbMax": "same"}},
    {"name": "Pirate Gaster", "blurb": "Dark, dark, yet darker. Now with a hat.", "wingdings": True,
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#2ba7b8", "accentOnTaskbar": True, "accentOnTitlebars": False, "live": "mine:pirate-gaster",
                  "tbStyle": "acrylic", "tbColor": "#0a2a30", "tbOpacity": 40, "tbMax": "same"}},
    {"name": "Cyber City", "blurb": "Big shot pink, everywhere.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#ff3ea5", "accentOnTaskbar": True, "accentOnTitlebars": True, "live": "mine:cyber-city",
                  "tbStyle": "acrylic", "tbColor": "#ff3ea5", "tbOpacity": 20, "tbMax": "same"}},
    {"name": "Field of Hopes", "blurb": "Ralsei green, soft and cozy.",
     "settings": {"cursors": "soul", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#2fbf71", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:field-of-hopes"}},
    {"name": "Neon Skyline", "blurb": "Night city glass. Blue with a pink glow.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "default",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#5b8cff", "accentOnTaskbar": True, "accentOnTitlebars": False,
                  "live": "mine:neon-skyline", "widgets": ["Clock", "Music", "Stats"],
                  "tbStyle": "acrylic", "tbColor": "#5b8cff", "tbOpacity": 15, "tbMax": "same"}},
    {"name": "Light World", "blurb": "Daytime in Hometown. Light mode.",
     "settings": {"cursors": "default", "icons": "default", "sounds": "default",
                  "appsDark": False, "systemDark": False, "transparency": True,
                  "accent": "#3b6fd8", "accentOnTaskbar": False, "accentOnTitlebars": False, "live": "mine:light-world",
                  "tbStyle": "normal", "tbMax": "same"}},
    {"name": "Card Castle", "blurb": "Hearts, spades and a very loud Lancer.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#8a5ae0", "accentOnTaskbar": True, "accentOnTitlebars": False, "live": "mine:card-castle",
                  "tbStyle": "acrylic", "tbColor": "#8a5ae0", "tbOpacity": 20, "tbMax": "same"}},
    {"name": "Queen's Mansion", "blurb": "Acid green. Very high tech. Very Queen.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#3cffb0", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:queens-mansion",
                  "tbStyle": "acrylic", "tbColor": "#0a3a2a", "tbOpacity": 35, "tbMax": "same"}},
    {"name": "TV World", "blurb": "Lights, curtains, ratings! Tenna is on.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#ffcc00", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:tv-world",
                  "tbStyle": "acrylic", "tbColor": "#3a0c1c", "tbOpacity": 40, "tbMax": "same"}},
    {"name": "Snowdin", "blurb": "Snowy night, warm windows, and the town song.",
     "settings": {"cursors": "soul", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#7fb8ff", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:snowdin",
                  "tbStyle": "acrylic", "tbColor": "#14285a", "tbOpacity": 30, "tbMax": "same"}},
    {"name": "Waterfall", "blurb": "Echo flowers glowing in the dark.",
     "settings": {"cursors": "soul", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#3cc8ff", "accentOnTaskbar": True, "accentOnTitlebars": False, "live": "mine:waterfall",
                  "tbStyle": "acrylic", "tbColor": "#08143a", "tbOpacity": 40, "tbMax": "same"}},
    {"name": "Judgment Hall", "blurb": "Golden light. It's a beautiful day outside.",
     "settings": {"cursors": "soul", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#e8b04a", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:judgment-hall",
                  "tbStyle": "acrylic", "tbColor": "#e8b04a", "tbOpacity": 15, "tbMax": "same"}},
    {"name": "Forgotten Man", "blurb": "A red tree, an egg, and his theme playing. Don't forget him.",
     "settings": {"cursors": "pixel-accent", "icons": "pixel", "sounds": "chiptune",
                  "appsDark": True, "systemDark": True, "transparency": True,
                  "accent": "#d0202e", "accentOnTaskbar": False, "accentOnTitlebars": True, "live": "mine:forgotten-man",
                  "tbStyle": "clear", "tbColor": "#000000", "tbOpacity": 0, "tbMax": "opaque"}},
]

# Hidden YouTube player used by wallpapers with music. Loops forever and
# listens for {winuxMusic, on, vol} messages from the wallpaper.
MUSIC_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin"></head>
<body style="margin:0;background:#000"><div id="p"></div>
<script>
let on = __ON__, vol = __VOL__, player = null;
function onYouTubeIframeAPIReady() {
  player = new YT.Player("p", {
    width: 200, height: 120, videoId: "__VID__",
    playerVars: { autoplay: 1, loop: 1, playlist: "__VID__", controls: 0, playsinline: 1 },
    events: {
      onReady: (e) => { e.target.setVolume(vol); e.target.unMute(); on ? e.target.playVideo() : e.target.pauseVideo(); },
      onStateChange: (e) => { if (e.data === 0) e.target.playVideo(); },
    },
  });
}
addEventListener("message", (e) => {
  const m = e.data || {};
  if (!m.winuxMusic || !player || !player.setVolume) return;
  on = m.on; vol = m.vol;
  player.setVolume(vol);
  on ? player.playVideo() : player.pauseVideo();
});
</script>
<script src="https://www.youtube.com/iframe_api"></script>
</body></html>"""


def list_themes():
    mine = []
    for f in sorted(THEMES.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            t["id"] = f.stem
            mine.append(t)
        except (OSError, ValueError):
            pass
    def extras(t):
        lid = (t.get("settings") or {}).get("live") or ""
        p = live_path(lid) if lid.startswith("mine:") else None
        info = read_info(p) if p and p.is_dir() else None
        return {**t, "extras": live_extras(info) if info else []}
    return {"presets": [extras(t) for t in PRESETS], "mine": [extras(t) for t in mine]}


def save_theme(name, settings, blurb=""):
    stem, _ = safe_name(name + ".json", "theme")
    data = {"name": name[:40], "blurb": blurb[:120], "settings": settings,
            "saved": time.strftime("%Y-%m-%d %H:%M")}
    (THEMES / (stem + ".json")).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return stem


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, ctype):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def send_big_file(self, path, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with open(path, "rb") as f:
            try:
                shutil.copyfileobj(f, self.wfile, 1024 * 1024)
            except (ConnectionError, OSError):
                pass  # the browser stopped watching, that's fine

    def allowed(self):
        # Only our own page may change settings: right host + secret token.
        host = self.headers.get("Host", "")
        return (host in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")
                and self.headers.get("X-WinUx-Token") == TOKEN)

    def read_body(self, limit):
        n = int(self.headers.get("Content-Length", 0))
        if n > limit:
            raise ValueError("too big")
        return self.rfile.read(n)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path in ("/", "/index.html"):
            html = (UI / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif url.path in ("/style.css", "/app.js"):
            self.send_file(UI / url.path[1:],
                           "text/css" if url.path.endswith(".css") else "text/javascript")
        elif url.path == "/wall":
            p = wallpaper_path(q.get("id", [""])[0])
            if not p:
                return self.send_json({"error": "not found"}, 404)
            ctype = {".png": "image/png", ".bmp": "image/bmp"}.get(p.suffix.lower(), "image/jpeg")
            self.send_file(p, ctype)
        elif url.path.startswith("/gen/"):
            # generated previews (png) and sounds (wav)
            p = (GENERATED / url.path[5:]).resolve()
            if not p.is_relative_to(GENERATED.resolve()) or not p.is_file() or p.suffix not in (".png", ".wav"):
                return self.send_json({"error": "not found"}, 404)
            self.send_file(p, "image/png" if p.suffix == ".png" else "audio/wav")
        elif url.path == "/livethumb":
            p = live_image(q.get("id", [""])[0], q.get("kind", ["thumb"])[0])
            if not p:
                return self.send_json({"error": "not found"}, 404)
            ctype = {".png": "image/png", ".gif": "image/gif"}.get(p.suffix.lower(), "image/jpeg")
            self.send_file(p, ctype)
        elif url.path == "/livefile":
            # Our own live wallpapers: the video/gif, or the web page for a preview.
            p = live_path(q.get("id", [""])[0])
            if not p or not p.is_relative_to(LIVE_WALLS.resolve()):
                return self.send_json({"error": "not found"}, 404)
            if p.is_dir():
                p = p / (read_info(p) or {}).get("FileName", "index.html")
                p = p.resolve()
                if not p.is_file() or not p.is_relative_to(LIVE_WALLS.resolve()):
                    return self.send_json({"error": "not found"}, 404)
            ctype = {".mp4": "video/mp4", ".webm": "video/webm", ".gif": "image/gif",
                     ".mov": "video/quicktime", ".mkv": "video/x-matroska",
                     ".html": "text/html; charset=utf-8"}.get(p.suffix.lower(), "application/octet-stream")
            self.send_big_file(p, ctype)
        elif url.path == "/music":
            # A tiny YouTube player for wallpapers with music (Forgotten Man).
            # YouTube refuses to play from file:// pages, so it lives here.
            vid = q.get("v", [""])[0]
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                return self.send_json({"error": "bad video"}, 400)
            vol = max(0, min(100, int(q.get("vol", ["50"])[0] or 50)))
            on = q.get("on", ["1"])[0] == "1"
            html = MUSIC_PAGE.replace("__VID__", vid).replace("__VOL__", str(vol)).replace("__ON__", "true" if on else "false")
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif not self.allowed():
            self.send_json({"error": "forbidden"}, 403)
        elif url.path == "/api/state":
            self.send_json({**get_state(), "backup": json.loads(ORIGINAL.read_text())["saved"]})
        elif url.path == "/api/wallpapers":
            self.send_json(list_wallpapers())
        elif url.path == "/api/themes":
            self.send_json(list_themes())
        elif url.path == "/api/live":
            self.send_json(list_live())
        elif url.path == "/api/mods":
            self.send_json(windhawk_mods())
        elif url.path == "/api/widgets":
            self.send_json(list_widgets())
        elif url.path == "/api/startup":
            self.send_json(startup_state())
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.allowed():
            return self.send_json({"error": "forbidden"}, 403)
        url = urlparse(self.path)
        try:
            if url.path == "/api/upload":
                # Raw image bytes; X-Filename says what it was called, X-Kind where it goes.
                stem, ext = safe_name(self.headers.get("X-Filename", "image.png"))
                kind = self.headers.get("X-Kind")
                if kind == "live":
                    if ext not in VIDEO_EXTS:
                        return self.send_json({"error": "Use an MP4, WEBM, MOV, MKV or GIF."}, 400)
                    folder, limit, prefix = LIVE_WALLS, 500 * 1024 * 1024, "mine:"
                else:
                    if ext not in IMAGE_EXTS:
                        return self.send_json({"error": "Use a PNG, JPG or BMP image."}, 400)
                    folder = ART_INBOX if kind == "art" else WALLPAPERS
                    limit, prefix = 60 * 1024 * 1024, "art:" if kind == "art" else "lib:"
                n_bytes = int(self.headers.get("Content-Length", 0))
                if n_bytes > limit:
                    return self.send_json({"error": "That file is too big."}, 400)
                target = folder / (stem + ext)
                n = 2
                while target.exists():
                    target = folder / f"{stem}-{n}{ext}"
                    n += 1
                with open(target, "wb") as out:  # stream it, videos can be big
                    left = n_bytes
                    while left > 0:
                        chunk = self.rfile.read(min(left, 1024 * 1024))
                        if not chunk:
                            break
                        out.write(chunk)
                        left -= len(chunk)
                return self.send_json({"id": prefix + target.name})

            body = json.loads(self.read_body(1024 * 1024) or b"{}")
            if url.path == "/api/apply":
                self.send_json(apply_settings(body))
            elif url.path == "/api/themes":
                name = str(body.get("name", "")).strip()
                if not name:
                    return self.send_json({"error": "Give your theme a name."}, 400)
                self.send_json({"id": save_theme(name, body.get("settings", {}),
                                                 str(body.get("blurb", "")))})
            elif url.path == "/api/restore":
                self.send_json(restore_original())
            elif url.path == "/api/widget":
                config = str(body.get("config", ""))
                known = {w["config"] for group in ("mine", "yours") for w in list_widgets()[group]}
                if config not in known:
                    return self.send_json({"error": "Unknown widget."}, 400)
                set_widget(config, bool(body.get("on")), body.get("file"))
                time.sleep(0.5)  # let Rainmeter save its settings
                self.send_json(list_widgets())
            elif url.path == "/api/lively-keyboard":
                set_lively_keyboard(bool(body.get("on")))
                self.send_json(get_state())
            elif url.path == "/api/startup":
                set_startup(str(body.get("key")), bool(body.get("on")))
                self.send_json(startup_state())
            elif url.path == "/api/windhawk/open":
                open_windhawk()
                self.send_json({"ok": True})
            elif url.path == "/api/refresh-taskbar":
                restart_explorer()
                self.send_json({"ok": True})
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as e:  # show the problem in the UI instead of hanging
            self.send_json({"error": str(e)}, 500)

    def do_DELETE(self):
        if not self.allowed():
            return self.send_json({"error": "forbidden"}, 403)
        url = urlparse(self.path)
        if url.path == "/api/themes":
            stem = re.sub(r"[^A-Za-z0-9 _-]", "", parse_qs(url.query).get("id", [""])[0])
            f = THEMES / (stem + ".json")
            if stem and f.exists():
                f.unlink()
            self.send_json({"ok": True})
        else:
            self.send_json({"error": "not found"}, 404)


def main():
    ensure_original_backup()
    assets.build_previews(get_state_accent())
    app_icons.preview_png(assets.OUT / "previews" / "app-icons.png", scale=2, gap=6)
    assets.build_sounds()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        # Already running - open the panel (unless we were started quietly, like at login).
        if "--no-browser" not in sys.argv:
            webbrowser.open(f"http://127.0.0.1:{PORT}/")
        return
    if "--no-browser" not in sys.argv:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    print(f"WinUx is running at http://127.0.0.1:{PORT}/  (close this window to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
