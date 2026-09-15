"""Windows helpers: sharp pixels on scaled screens, where the pet can walk, fullscreen apps,
and a window that stays on top without stealing focus or appearing in Alt+Tab."""
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.WinDLL('user32', use_last_error=True)

user32.GetForegroundWindow.restype = wt.HWND
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.GetParent.argtypes = [wt.HWND]
user32.GetParent.restype = wt.HWND
user32.SystemParametersInfoW.argtypes = [wt.UINT, wt.UINT, ctypes.c_void_p, wt.UINT]
user32.GetDpiForSystem.restype = wt.UINT

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, WS_EX_NOACTIVATE = 0x80, 0x40, 0x08000000
HWND_TOPMOST = wt.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
SPI_GETWORKAREA = 0x30
MONITOR_DEFAULTTONEAREST, MONITORINFOF_PRIMARY = 2, 1
SHELL_WINDOWS = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'}


class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', wt.RECT), ('rcWork', wt.RECT), ('dwFlags', wt.DWORD)]


def make_dpi_aware():
    """Work in real screen pixels, so pixel art isn't blurred by Windows scaling."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def screen_dpi():
    try:
        return user32.GetDpiForSystem() or 96
    except (AttributeError, OSError):
        return 96


def fine_timer(on):
    """1 ms timer resolution while running, for evenly spaced animation frames."""
    try:
        winmm = ctypes.windll.winmm
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)
    except (AttributeError, OSError):
        pass


def walk_area():
    """(left, right, floor) on the main screen. With the taskbar at the bottom the floor is its top
    edge; with it hidden or on another side, the floor is the bottom of the screen."""
    rc = wt.RECT()
    if not user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rc), 0):
        return 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    return rc.left, rc.right, rc.bottom


def fullscreen_app_on_main_screen():
    """True while a game or video fills the main screen (the pet hides then)."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, name, 64)
    if name.value in SHELL_WINDOWS:
        return False
    rect = wt.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False
    m = info.rcMonitor
    covers = rect.left <= m.left and rect.top <= m.top and rect.right >= m.right and rect.bottom >= m.bottom
    return covers and bool(info.dwFlags & MONITORINFOF_PRIMARY)


def top_level_handle(tk_window):
    hwnd = user32.GetParent(tk_window.winfo_id())
    return hwnd or tk_window.winfo_id()


def style_pet_window(hwnd):
    """No taskbar button, not in Alt+Tab, and clicking it never takes focus from what you're doing."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = (style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
SW_HIDE, SW_SHOWNOACTIVATE = 0, 4


def show(hwnd, visible):
    """Show or hide without activating (so a game never loses focus to the pet)."""
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE if visible else SW_HIDE)


kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
kernel32.CreateMutexW.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
_instance = None


def single_instance(name='Local\\ClaudePetInstance'):
    """True if this is the only pet running (a second copy just exits)."""
    global _instance
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return False
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _instance = handle
    return True


def release_instance():
    """Let a new copy start (used when the pet restarts itself, e.g. after changing size)."""
    global _instance
    if _instance:
        kernel32.CloseHandle(_instance)
        _instance = None


def place(hwnd, x, y):
    """Move the window and keep it above other windows (including the taskbar)."""
    user32.SetWindowPos(hwnd, HWND_TOPMOST, int(x), int(y), 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
