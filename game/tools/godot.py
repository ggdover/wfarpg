"""Running Godot from the tools (checks.py, play.py, export_windows.py) the same on Linux and Windows: finding it, and
choosing the screen the game's window opens on, which they say as they start (`screen: ...`)."""
import os
import shutil
import sys


def exe():
    """Godot 4.7: $GODOT, else godot on PATH (on Windows, its console build or a godot.cmd that runs it), else the one
    in ~/.local/bin, which a terminal opened before that went on PATH doesn't see."""
    found = (os.environ.get("GODOT") or shutil.which("godot")
             or shutil.which("godot", path=os.path.join(os.path.expanduser("~"), ".local", "bin")))
    if not found:
        sys.exit("Godot 4.7 not found: put godot on PATH (and reopen the terminal), or set GODOT to it (README.md)")
    return found


def take_screen(args):
    """Takes the --screen option out of args (--screen=X or --screen X; the last counts) and says what it asks for, or
    that there's none, so claude: Godot's arguments for that (screen_args), and the rest of args."""
    given, rest, words = [], [], iter(args)
    for word in words:
        if word.startswith("--screen="):
            given.append((word, word.removeprefix("--screen=")))
        elif word == "--screen":
            value = next(words, "")
            given.append((f"--screen {value}", value))
        else:
            rest.append(word)
    if not given:
        say("no --screen given, so the default, claude (the monitor the Claude app is on)")
        return screen_args("claude"), rest
    shown, value = given[-1]
    asks = ("the monitor the Claude app is on" if value == "claude" else "the primary screen" if value == "primary"
            else f"screen {value}, as Godot counts them from 0" if value.isdigit() else None)
    if asks is None:
        sys.exit(f"--screen takes claude, primary or a screen's number (Godot counts them from 0), not {value!r}")
    say(f"{shown} given{f', the last of {len(given)}' if len(given) > 1 else ''} ({asks})")
    return screen_args(value), rest


def screen_args(value):
    """Godot's arguments for a --screen value, saying where its window opens: claude for the monitor the Claude app's
    window is on (looked for on Windows; without one, the primary), primary, or a screen's number, as Godot counts them
    (from 0, in the order the OS lists the monitors, so 0 needn't be the primary). [] leaves the window where Godot
    puts it, on the primary."""
    if value == "claude":
        screen = claude_screen()
        if screen is not None:
            say(f"the Claude app's window is on screen {screen}{about(screen)}: Godot opens there, "
                f"with --screen {screen}")
            return ["--screen", str(screen)]
        why = ("no window of the Claude app to be found" if sys.platform == "win32"
               else "the Claude app's window is looked for on Windows only")
        say(f"{why}, so Godot opens on {the_primary()}, with no --screen")
        return []
    if value == "primary":
        say(f"Godot opens on {the_primary()}, with no --screen")
        return []
    say(f"Godot opens on screen {value}{about(int(value))}, with --screen {value}")
    return ["--screen", value]


def say(line):
    print("screen: " + line, flush=True)


def about(screen):
    """' (its name, size, and where it is beside the primary)' for a screen as Godot numbers them, on Windows; ''
    elsewhere, where the monitors aren't looked at."""
    found = monitors()
    if not found:
        return ""
    if screen >= len(found):
        return f" (no such screen: Windows lists {len(found)}, from 0)"
    _, name, (left, top, right, bottom), is_primary = found[screen]
    p_left, p_top, p_right, p_bottom = next((m[2] for m in found if m[3]), found[screen][2])
    side = ("the primary" if is_primary else "left of the primary" if right <= p_left
            else "right of the primary" if left >= p_right else "above the primary" if bottom <= p_top
            else "below the primary" if top >= p_bottom else "beside the primary")
    return f" ({name}, {right - left}x{bottom - top}, {side})"


def the_primary():
    """'the primary', and on Windows which screen that is, as Godot numbers them."""
    for i, (_, name, (left, top, right, bottom), is_primary) in enumerate(monitors()):
        if is_primary:
            return f"the primary, screen {i} ({name}, {right - left}x{bottom - top})"
    return "the primary"


def claude_screen():
    """The screen the Claude app's window is on, numbered as Godot numbers them, or None: it's looked for on Windows."""
    return window_screen("claude.exe") if sys.platform == "win32" else None


def window_screen(program):
    """Windows: the screen the biggest visible window of program (an .exe's name) is on, or will come back to if it's
    minimized, numbered in the order Windows lists the monitors, which is Godot's order. None if it has no window."""
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
    for name, args in (("IsWindowVisible", [wintypes.HWND]), ("IsIconic", [wintypes.HWND]),
                       ("GetWindowTextLengthW", [wintypes.HWND]), ("GetWindowRect", [wintypes.HWND, ctypes.c_void_p]),
                       ("GetWindowPlacement", [wintypes.HWND, ctypes.c_void_p]),
                       ("GetWindowThreadProcessId", [wintypes.HWND, ctypes.c_void_p]),
                       ("MonitorFromWindow", [wintypes.HWND, wintypes.DWORD]),
                       ("MonitorFromRect", [ctypes.c_void_p, wintypes.DWORD])):
        getattr(user32, name).argtypes = args
    user32.MonitorFromWindow.restype = user32.MonitorFromRect.restype = wintypes.HANDLE
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    class Placement(ctypes.Structure):  # WINDOWPLACEMENT
        _fields_ = [("length", wintypes.UINT), ("flags", wintypes.UINT), ("show", wintypes.UINT),
                    ("min_position", wintypes.POINT), ("max_position", wintypes.POINT), ("normal", wintypes.RECT)]

    def program_of(hwnd):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not process:
            return ""
        path, size = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
        ok = kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size))
        kernel32.CloseHandle(process)
        return os.path.basename(path.value).lower() if ok else ""

    found = []  # (area, monitor) of each of program's windows

    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) and program_of(hwnd) == program.lower():
            if user32.IsIconic(hwnd):
                placement = Placement(length=ctypes.sizeof(Placement))
                user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
                rect = placement.normal
                monitor = user32.MonitorFromRect(ctypes.byref(rect), 2)  # MONITOR_DEFAULTTONEAREST
            else:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                monitor = user32.MonitorFromWindow(hwnd, 2)
            found.append(((rect.right - rect.left) * (rect.bottom - rect.top), monitor))
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(visit), 0)
    if not found:
        return None
    handles = [m[0] for m in monitors()]
    monitor = max(found)[1]
    return handles.index(monitor) if monitor in handles else None


def monitors():
    """Windows: the monitors, in the order Windows lists them, which is the order Godot numbers its screens in, each as
    (handle, name, (left, top, right, bottom), whether it's the primary). [] elsewhere."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    class Info(ctypes.Structure):  # MONITORINFOEXW
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT), ("work", wintypes.RECT),
                    ("flags", wintypes.DWORD), ("device", wintypes.WCHAR * 32)]

    user32 = ctypes.WinDLL("user32")
    user32.SetProcessDPIAware()  # the monitors' own pixels, not ones scaled for a program that doesn't know of scaling
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    found = []

    def collect(monitor, _dc, _rect, _data):
        info = Info(size=ctypes.sizeof(Info))
        user32.GetMonitorInfoW(monitor, ctypes.byref(info))
        r, primary = info.monitor, bool(info.flags & 1)  # MONITORINFOF_PRIMARY
        found.append((monitor, info.device, (r.left, r.top, r.right, r.bottom), primary))
        return True

    user32.EnumDisplayMonitors(None, None, ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                                              ctypes.c_void_p, wintypes.LPARAM)(collect), 0)
    return found
