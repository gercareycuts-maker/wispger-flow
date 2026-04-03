"""Reusable UI widgets: Tooltip, StatusDot, TranscriptionCard, RecordingOverlay, emoji cache."""

import math
import tkinter as tk

import customtkinter as ctk
import pyperclip

from wispger_flow.constants import IS_WIN, IS_MAC, F, _screen_size, _scroll_units
from wispger_flow.ui.theme import ACCENT, ACCENTH, TEAL, GREEN, RED, REDDIM, AMBER, DARK
from wispger_flow.core.stats import ACHIEVEMENTS

# -- Achievement emoji images --
_ACH_EMOJI_CACHE = {}


def render_emoji_images():
    """Load cached emoji PNGs from disk, or render and cache them on first run."""
    from PIL import Image, ImageDraw, ImageFont
    from wispger_flow.constants import CFG_DIR

    cache_dir = CFG_DIR / "emoji_cache"
    icons = {icon for _, _, _, icon, _, _, _ in ACHIEVEMENTS}

    # Try loading from disk cache first
    if cache_dir.exists():
        all_cached = True
        for char in icons:
            path = cache_dir / f"{ord(char):x}.png"
            if path.exists():
                try:
                    _ACH_EMOJI_CACHE[char] = Image.open(path).copy()
                    continue
                except Exception:
                    pass
            all_cached = False
        if all_cached:
            return

    # Render fresh and save to disk
    if IS_WIN:
        font_path = "seguiemj.ttf"
    elif IS_MAC:
        font_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    else:
        font_path = None
    try:
        font = ImageFont.truetype(font_path, 109) if font_path else None
    except Exception:
        font = None

    cache_dir.mkdir(parents=True, exist_ok=True)
    canvas_size = 56
    emoji_size = 44
    for char in icons:
        if char in _ACH_EMOJI_CACHE:
            continue
        if font:
            tmp = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tmp)
            draw.text((80, 80), char, font=font, embedded_color=True)
            bbox = tmp.getbbox()
            if bbox:
                glyph = tmp.crop(bbox)
                w, h = glyph.size
                scale = emoji_size / max(w, h)
                nw, nh = int(w * scale), int(h * scale)
                glyph = glyph.resize((nw, nh), Image.LANCZOS)
                result = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
                result.paste(glyph, ((canvas_size - nw) // 2, (canvas_size - nh) // 2))
                _ACH_EMOJI_CACHE[char] = result
                try:
                    result.save(cache_dir / f"{ord(char):x}.png")
                except Exception:
                    pass
            else:
                _ACH_EMOJI_CACHE[char] = None
        else:
            _ACH_EMOJI_CACHE[char] = None


# -- Tooltip --
class Tooltip:
    def __init__(self, widget, text):
        self._w, self._text, self._tw, self._after_id = widget, text, None, None
        self._mx, self._my = 0, 0
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)
        widget.bind("<Motion>", self._motion)
        for child in widget.winfo_children():
            child.bind("<Enter>", self._enter)
            child.bind("<Leave>", self._leave)
            child.bind("<Motion>", self._motion)

    def _enter(self, e):
        self._mx, self._my = e.x_root, e.y_root
        if not self._after_id:
            self._after_id = self._w.after(100, self._show)

    def _leave(self, e):
        if self._after_id:
            self._w.after_cancel(self._after_id)
            self._after_id = None
        if self._tw:
            self._tw.destroy()
            self._tw = None

    def _motion(self, e):
        self._mx, self._my = e.x_root, e.y_root
        if self._tw:
            self._tw.geometry(f"+{self._mx + 14}+{self._my + 18}")

    def _show(self):
        self._after_id = None
        if self._tw:
            return
        self._tw = tw = tk.Toplevel(self._w)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        if IS_WIN:
            try:
                tw.wm_attributes("-disabled", True)
            except Exception:
                pass
        tw.configure(bg="#1a1a2e")
        tk.Label(tw, text=self._text, bg="#1a1a2e", fg="#e8e8f0", font=(F, 8),
                 padx=8, pady=4, wraplength=200, justify="left").pack()
        tw.update_idletasks()
        tw.geometry(f"+{self._mx + 14}+{self._my + 18}")


# -- Recording Overlay --
class RecordingOverlay(tk.Toplevel):
    W, H, N, GAP = 220, 56, 18, 2

    def __init__(self, parent, rec):
        super().__init__(parent)
        self._rec, self._active, self._h, self._ph = rec, False, [0.0] * self.N, 0.0
        self._fill = DARK["overlay"]
        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", 0.90)
        if IS_WIN:
            self.configure(bg="#010101")
            self.wm_attributes("-transparentcolor", "#010101")
            cbg = "#010101"
        elif IS_MAC:
            self.wm_attributes("-transparent", True)
            self.configure(bg="systemTransparent")
            cbg = "systemTransparent"
        else:
            self.configure(bg="#010101")
            cbg = "#010101"
        self._c = tk.Canvas(self, width=self.W, height=self.H, bg=cbg, highlightthickness=0, bd=0)
        self._c.pack(fill="both", expand=True)
        self.withdraw()

    def set_theme(self, t):
        self._fill = t["overlay"]

    def _pos(self):
        if IS_WIN:
            sw, sh = _screen_size()
        else:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{(sw - self.W) // 2}+{sh - self.H - 50}")

    def _rr(self, x0, y0, x1, y1, r, **kw):
        c = self._c
        for sx, sy, a in [(x0, y0, 90), (x1 - 2 * r, y0, 0), (x0, y1 - 2 * r, 180), (x1 - 2 * r, y1 - 2 * r, 270)]:
            c.create_arc(sx, sy, sx + 2 * r, sy + 2 * r, start=a, extent=90, style="pieslice", **kw)
        c.create_rectangle(x0 + r, y0, x1 - r, y1, **kw)
        c.create_rectangle(x0, y0 + r, x1, y1 - r, **kw)

    def show(self):
        import time as _time
        self._active, self._ph, self._h = True, 0.0, [0.0] * self.N
        self._start_time = _time.time()
        self._pos()
        self.deiconify()
        self.lift()
        self._tick()

    def hide(self):
        self._active = False
        self.withdraw()

    def _tick(self):
        if not self._active:
            return
        self._c.delete("b")
        self._rr(0, 0, self.W, self.H, 14, fill=self._fill, outline="", tags="b")
        lv, self._ph = min(self._rec.level * 50, 1.0), self._ph + 0.25
        bw, mh, cx = (self.W - 20) / self.N - self.GAP, self.H - 8, self.N / 2
        for i in range(self.N):
            d = abs(i - cx) / cx
            t = lv * (math.sin(self._ph + i * 0.5) * 0.4 + 0.6) * (1 - d * 0.4) * mh
            self._h[i] += (max(t, 2) - self._h[i]) * 0.7
            h = self._h[i]
            x0, br = 10 + i * (bw + self.GAP), 1 - d * 0.35
            self._c.create_rectangle(
                x0, (self.H - h) / 2, x0 + bw, (self.H + h) / 2, tags="b", outline="",
                fill=f"#{int(230 * br):02x}{int(126 * br):02x}{int(34 * br):02x}",
            )
        import time as _time
        elapsed = int(_time.time() - self._start_time)
        time_str = f"{elapsed // 60}:{elapsed % 60:02d}"
        self._c.create_text(self.W - 18, self.H // 2, text=time_str, fill="#e8e8f0",
                            font=(F, 11, "bold"), anchor="e", tags="b")
        self.after(25, self._tick)


# -- Transcription Card --
class TranscriptionCard(ctk.CTkFrame):
    def __init__(self, parent, text, dur, ts, t, animate=False, on_edit=None):
        super().__init__(parent, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"])
        self._text, self._t, self._ts, self._dur = text, t, ts, dur
        self._on_edit = on_edit
        self._editing = False
        self._border_normal, self._border_hover = t["border"], t["txt2"]

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(hdr, text="\u223f", font=(F, 16, "bold"), text_color=ACCENT).pack(side="left")
        day = ts.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        date_str = ts.strftime(f"%A {day}{suffix} %B %I:%M%p").replace("AM", "am").replace("PM", "pm")
        ctk.CTkLabel(hdr, text=date_str, font=(F, 11), text_color=t["txt2"]).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(hdr, text=f"{dur:.1f}s", font=(F, 11, "bold"), text_color="#fff",
                     fg_color=TEAL, corner_radius=8, width=50, height=24).pack(side="right")

        self._text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._text_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._text_lbl = ctk.CTkLabel(self._text_frame, text=text, font=(F, 13), text_color=t["txt"],
                                       wraplength=380, justify="left", anchor="w", cursor="hand2")
        self._text_lbl.pack(side="left", fill="x", expand=True)
        self._edit_icon = ctk.CTkLabel(self._text_frame, text="\u270e", font=(F, 16), text_color=t["dim"],
                                        cursor="hand2", width=28)
        self._text_lbl.bind("<Button-1>", lambda e: self._start_edit())
        self._edit_icon.bind("<Button-1>", lambda e: self._start_edit())

        self._btn = ctk.CTkButton(self, text="\u2398  Copy", width=95, height=32, corner_radius=8,
                                  font=(F, 12, "bold"), fg_color=ACCENT, hover_color=ACCENTH, command=self._copy)
        self._btn.pack(anchor="e", padx=16, pady=(0, 14))

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        if animate:
            self._fade_in()

    def _on_enter(self, e):
        self.configure(border_color=self._border_hover)
        if not self._editing:
            self._edit_icon.pack(side="right", padx=(4, 0))

    def _on_leave(self, e):
        self.configure(border_color=self._border_normal)
        if not self._editing:
            self._edit_icon.pack_forget()

    def update_theme(self, t):
        self._t = t
        self._border_normal = t["border"]
        self._border_hover = t["txt2"]
        self.configure(fg_color=t["card"], border_color=self._border_normal)
        try:
            self._bg_color = self._detect_color_of_master()
            self._draw()
        except Exception:
            pass
        # Update text label and edit icon colours
        self._text_lbl.configure(text_color=t["txt"])
        self._edit_icon.configure(text_color=t["dim"])

    def _start_edit(self):
        if self._editing:
            return
        self._editing = True
        t = self._t
        self._edit_icon.pack_forget()
        self._text_lbl.pack_forget()
        self._edit_box = ctk.CTkTextbox(self._text_frame, font=(F, 13), fg_color=t["bg"],
                                         border_color=ACCENT, border_width=1, text_color=t["txt"],
                                         corner_radius=8, height=max(60, min(120, len(self._text) // 3)))
        self._edit_box.pack(fill="x", expand=True)
        self._edit_box.insert("1.0", self._text)
        self._edit_box.focus_set()
        self._edit_box.bind("<Return>", lambda e: (self._finish_edit(), "break")[1])
        self._edit_box.bind("<FocusOut>", lambda e: self._finish_edit())

    def _finish_edit(self):
        if not self._editing:
            return
        self._editing = False
        new_text = self._edit_box.get("1.0", "end").strip()
        self._edit_box.destroy()
        if new_text and new_text != self._text:
            self._text = new_text
            self._text_lbl.configure(text=new_text)
            if self._on_edit:
                self._on_edit(self._ts, new_text)
        self._text_lbl.pack(side="left", fill="x", expand=True)

    def _fade_in(self):
        bg = self._t["bg"]
        card = self._t["card"]
        steps = 8

        def _lerp_hex(a, b, p):
            ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
            br, bg_, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
            return f"#{int(ar + (br - ar) * p):02x}{int(ag + (bg_ - ag) * p):02x}{int(ab + (bb - ab) * p):02x}"

        def _step(i=0):
            if i > steps:
                return
            p = i / steps
            self.configure(fg_color=_lerp_hex(bg, card, p))
            self.after(25, lambda: _step(i + 1))
        _step()

    def _copy(self):
        pyperclip.copy(self._text)
        self._btn.configure(text="\u2713  Copied!", fg_color=GREEN)
        self.after(1500, lambda: self._btn.configure(text="\u2398  Copy", fg_color=ACCENT))


# -- Status Dot --
class StatusDot(ctk.CTkFrame):
    def __init__(self, parent, t):
        super().__init__(parent, fg_color="transparent")
        self._dot = ctk.CTkLabel(self, text="\u25cf", font=(F, 10), text_color=TEAL, width=16)
        self._dot.pack(side="left")
        self._default_color = t["txt2"]
        self._lbl = ctk.CTkLabel(self, text="Ready", font=(F, 11), text_color=t["txt2"])
        self._lbl.pack(side="left", padx=(4, 0))
        self._pulsing = self._on = False

    def ready(self):
        self._pulsing = False
        self._dot.configure(text_color=TEAL)
        self._lbl.configure(text="Ready", text_color=self._default_color)

    def recording(self):
        self._pulsing = True
        self._lbl.configure(text="Recording", text_color=RED)
        self._pulse()

    def processing(self):
        self._pulsing = False
        self._dot.configure(text_color=AMBER)
        self._lbl.configure(text="Processing...", text_color=AMBER)

    def error(self, m="Error"):
        self._pulsing = False
        self._dot.configure(text_color=RED)
        self._lbl.configure(text=m, text_color=RED)

    def _pulse(self):
        if not self._pulsing:
            return
        self._on = not self._on
        self._dot.configure(text_color=RED if self._on else REDDIM)
        self.after(500, self._pulse)
