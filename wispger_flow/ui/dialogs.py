"""Dialog windows: API key setup, hotkey capture."""

import customtkinter as ctk
from pynput import keyboard

from wispger_flow.constants import IS_MAC, F
from wispger_flow.ui.theme import ACCENT, ACCENTH, RED
from wispger_flow.services.storage import load_cfg


class ApiKeyDialog(ctk.CTkToplevel):
    def __init__(self, parent, t):
        super().__init__(parent)
        self.title("WispGer Flow \u2014 Setup")
        self.geometry("420x280")
        self.configure(fg_color=t["bg"])
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        ctk.CTkLabel(self, text="\u223f", font=(F, 36, "bold"), text_color=ACCENT).pack(pady=(24, 8))
        ctk.CTkLabel(self, text="Enter your Groq API key", font=(F, 16, "bold"), text_color=t["txt"]).pack()
        ctk.CTkLabel(self, text="Free signup at groq.com \u2192 API Keys", font=(F, 11), text_color=t["dim"]).pack(pady=(4, 16))
        self._e = ctk.CTkEntry(self, width=340, height=38, font=(F, 12), placeholder_text="gsk_...",
                               fg_color=t["card"], border_color=t["border"], text_color=t["txt"])
        self._e.pack()
        self._e.bind("<Return>", lambda _: self._ok())
        self._err = ctk.CTkLabel(self, text="", font=(F, 10), text_color=RED)
        self._err.pack(pady=(4, 0))
        ctk.CTkButton(self, text="Save & Start", width=160, height=36, corner_radius=8,
                      font=(F, 12, "bold"), fg_color=ACCENT, hover_color=ACCENTH, command=self._ok).pack(pady=(12, 0))
        self.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "result", None), self.destroy()))

    def _ok(self):
        k = self._e.get().strip()
        if not k:
            self._err.configure(text="Please enter an API key")
        elif not k.startswith("gsk_"):
            self._err.configure(text="Key should start with gsk_")
        else:
            self.result = k
            self.destroy()


class HotkeyDialog(ctk.CTkToplevel):
    """Interactive hotkey capture dialog. Sets self.result to the combo string or None."""

    def __init__(self, parent, t):
        super().__init__(parent)
        self.title("Set Custom Hotkey")
        self.geometry("360x220")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color=t["bg"])
        self.grab_set()
        self.result = None

        ctk.CTkLabel(self, text="Press your hotkey combination", font=(F, 14, "bold"), text_color=t["txt"]).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="Hold 2 or more keys together", font=(F, 10), text_color=t["dim"]).pack(pady=(0, 16))

        keys_var = ctk.StringVar(value="Waiting...")
        ctk.CTkLabel(self, textvariable=keys_var, font=(F, 20, "bold"), text_color=ACCENT).pack(pady=(0, 20))

        held = set()
        captured = [None]

        _KEY_NAMES = {
            keyboard.Key.ctrl_l: "ctrl", keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
            keyboard.Key.alt_l: "alt", keyboard.Key.alt_r: "alt", keyboard.Key.alt_gr: "alt",
            keyboard.Key.cmd: "cmd" if IS_MAC else "win",
            keyboard.Key.cmd_r: "cmd" if IS_MAC else "win",
        }

        def _name(key):
            if key in _KEY_NAMES:
                return _KEY_NAMES[key]
            try:
                return key.char.lower() if key.char else str(key)
            except AttributeError:
                n = key.name if hasattr(key, "name") else str(key)
                return n.lower().replace("key.", "")

        def _display():
            if held:
                combo = "+".join(dict.fromkeys(held))
                keys_var.set(combo.replace("ctrl", "Ctrl").replace("win", "Win").replace("cmd", "Cmd")
                             .replace("shift", "Shift").replace("alt", "Alt"))
            else:
                keys_var.set("Waiting...")

        def _on_press(key):
            name = _name(key)
            held.add(name)
            if len(held) >= 2:
                captured[0] = "+".join(dict.fromkeys(held))
            self.after(0, _display)

        def _on_release(key):
            held.discard(_name(key))
            self.after(0, _display)

        self._listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
        self._listener.daemon = True
        self._listener.start()

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=(0, 16))

        def _confirm():
            self._listener.stop()
            self.result = captured[0]
            self.destroy()

        def _cancel():
            self._listener.stop()
            self.result = None
            self.destroy()

        ctk.CTkButton(btn_f, text="Confirm", width=100, height=32, corner_radius=8, font=(F, 11, "bold"),
                      fg_color=ACCENT, hover_color=ACCENTH, command=_confirm).pack(side="left", padx=8)
        ctk.CTkButton(btn_f, text="Cancel", width=100, height=32, corner_radius=8, font=(F, 11, "bold"),
                      fg_color=t["border"], hover_color=t["dim"], command=_cancel).pack(side="left", padx=8)
        self.protocol("WM_DELETE_WINDOW", _cancel)
