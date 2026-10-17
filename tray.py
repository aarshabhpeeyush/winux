"""WinUx tray icon + hotkey, using plain Windows calls (no extra packages).

- A red soul in the system tray. Right-click (or left-click) for a menu:
  open the panel, pick any theme, next theme, quit.
- Ctrl+Alt+T switches to the next theme from anywhere.

Everything runs on its own thread with its own Windows message loop. Theme
switching is handed to a worker thread so the menu never freezes.
"""
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.LPVOID]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class GUID(ctypes.Structure):
    _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256), ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD), ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON)]


WM_DESTROY, WM_CLOSE, WM_COMMAND, WM_HOTKEY, WM_NULL = 0x0002, 0x0010, 0x0111, 0x0312, 0x0000
WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_RBUTTONUP, WM_LBUTTONUP = 0x0205, 0x0202
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 1, 2, 4, 0x10
MF_STRING, MF_SEPARATOR, MF_POPUP, MF_CHECKED = 0, 0x800, 0x10, 0x8
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x2, 0x100
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
HOTKEY_ID = 1
ID_OPEN, ID_NEXT, ID_QUIT, ID_THEME = 1, 2, 3, 100


class Tray:
    """start() it once. `themes()` -> [(name, settings)], `apply(name, settings)`,
    `current()` -> name of the theme in use (or None), `open_panel()`, `quit()`."""

    def __init__(self, icon_path, themes, apply, current, open_panel, quit, hotkey=True):
        self.icon_path, self.themes, self.apply_cb = str(icon_path), themes, apply
        self.current, self.open_panel, self.quit_cb, self.hotkey = current, open_panel, quit, hotkey
        self.hwnd = None
        self.hotkey_ok = False
        self._proc = WNDPROC(self._wndproc)   # keep a reference so it isn't garbage collected

    def start(self):
        threading.Thread(target=self._run, daemon=True, name="winux-tray").start()

    # --- window + icon
    def _run(self):
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName="WinUxTray")
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, "WinUxTray", "WinUx", 0, 0, 0, 0, 0, None, None, hinst, None)
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        self.hicon = user32.LoadImageW(None, self.icon_path, 1, 16, 16, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
        self._icon(NIM_ADD)
        if self.hotkey:
            self.hotkey_ok = bool(user32.RegisterHotKey(self.hwnd, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord("T")))
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _nid(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd, nid.uID = self.hwnd, 1
        return nid

    def _icon(self, action):
        nid = self._nid()
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.hicon
        nid.szTip = "WinUx" + ("  (Ctrl+Alt+T: next theme)" if self.hotkey_ok or self.hotkey else "")
        shell32.Shell_NotifyIconW(action, ctypes.byref(nid))

    def notify(self, title, text):
        """A little Windows notification from the tray icon."""
        if not self.hwnd:
            return
        nid = self._nid()
        nid.uFlags = NIF_INFO
        nid.szInfoTitle, nid.szInfo = title[:63], text[:255]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    # --- events
    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY and lparam in (WM_RBUTTONUP, WM_LBUTTONUP):
            self._menu()
            return 0
        if msg == WM_HOTKEY and wparam == HOTKEY_ID:
            self._next()
            return 0
        if msg == self.taskbar_created:          # Explorer restarted: put the icon back
            self._icon(NIM_ADD)
            return 0
        if msg == WM_CLOSE:
            user32.UnregisterHotKey(hwnd, HOTKEY_ID)
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid()))
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _menu(self):
        themes = self.themes()
        now = self.current()
        menu = user32.CreatePopupMenu()
        sub = user32.CreatePopupMenu()
        for i, (name, _) in enumerate(themes):
            user32.AppendMenuW(sub, MF_STRING | (MF_CHECKED if name == now else 0), ID_THEME + i, name)
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN, "Open WinUx")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_POPUP, sub, "Themes")
        user32.AppendMenuW(menu, MF_STRING, ID_NEXT, "Next theme\tCtrl+Alt+T")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT, "Quit WinUx")
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)           # so the menu closes when you click away
        cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD, pt.x, pt.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
        if cmd == ID_OPEN:
            self.open_panel()
        elif cmd == ID_NEXT:
            self._next()
        elif cmd == ID_QUIT:
            self.stop()
            self.quit_cb()
        elif cmd >= ID_THEME and cmd - ID_THEME < len(themes):
            self._switch(*themes[cmd - ID_THEME])

    def _next(self):
        themes = self.themes()
        if not themes:
            return
        names = [n for n, _ in themes]
        now = self.current()
        i = (names.index(now) + 1) % len(names) if now in names else 0
        self._switch(*themes[i])

    def _switch(self, name, settings):
        def work():
            try:
                self.apply_cb(name, settings)
                self.notify("WinUx", f"Switched to {name}.")
            except Exception as e:     # never let a bad theme kill the tray
                self.notify("WinUx", f"Couldn't switch: {e}")
        threading.Thread(target=work, daemon=True).start()
