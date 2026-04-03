"""Platform detection, paths, font loading, DPI, and scroll helpers."""

import os
import sys
import tkinter as tk
from pathlib import Path

# -- Platform --
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

if IS_WIN:
    import ctypes

# -- Paths --
# In frozen builds, sys._MEIPASS is the bundle root.
# In dev, fonts/ lives next to main.py (repo root), which is one level up from this package.
APP_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent.parent
if IS_WIN:
    CFG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "WispGer"
elif IS_MAC:
    CFG_DIR = Path.home() / "Library" / "Application Support" / "WispGer"
else:
    CFG_DIR = Path.home() / ".config" / "WispGer"
CFG_FILE = CFG_DIR / "config.json"

# -- Font loading (side effect at import time) --
if IS_WIN:
    for _ttf in (APP_DIR / "fonts").glob("*.ttf"):
        ctypes.windll.gdi32.AddFontResourceExW(str(_ttf), 0x10, 0)
    F = "Poppins"
elif IS_MAC:
    _user_fonts = Path.home() / "Library" / "Fonts"
    for _ttf in (APP_DIR / "fonts").glob("*.ttf"):
        _dst = _user_fonts / _ttf.name
        if not _dst.exists():
            try:
                import shutil
                _user_fonts.mkdir(exist_ok=True)
                shutil.copy2(_ttf, _dst)
            except Exception:
                pass
    F = "Poppins"
else:
    F = "Poppins"

# -- DPI awareness --
if IS_WIN:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    def _screen_size():
        return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
else:
    def _screen_size():
        if not hasattr(_screen_size, "_c"):
            try:
                r = tk.Tk(); r.withdraw()
                _screen_size._c = (r.winfo_screenwidth(), r.winfo_screenheight()); r.destroy()
            except Exception:
                _screen_size._c = (1920, 1080)
        return _screen_size._c

def _scroll_units(event):
    if IS_MAC:
        return int(-1 * event.delta)
    return int(-1 * (event.delta / 90))

# -- Hotkey label --
HOTKEY = "Ctrl+Cmd" if IS_MAC else "Ctrl+Win"

# -- Default Whisper prompt (used when voice profile is empty) --
WHISPER_PROMPT = "Hello, how are you? I'm doing well. Yes, that sounds great! Let me think about it. Okay, I'll do that."
