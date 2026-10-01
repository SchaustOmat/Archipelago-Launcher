"""Dark purple ttk theme and a dark Windows title bar."""
import ctypes
import tkinter as tk
from tkinter import ttk

BG = "#1b1428"        # window
PANEL = "#241a38"     # frames
FIELD = "#140e20"     # entries, log, list
BORDER = "#3a2c5c"
FG = "#ece6ff"
MUTED = "#a497c7"
ACCENT = "#8b5cf6"
ACCENT_HI = "#a78bfa"
BUTTON = "#3a2a62"
BUTTON_HI = "#4c3780"
DISABLED = "#5d5480"
OK = "#5ee0a0"
WARN = "#ffb35c"
ERR = "#ff6b86"
FONT = ("Segoe UI", 10)


def apply(root: tk.Tk):
    root.configure(bg=BG)
    root.option_add("*Font", FONT)
    # Combobox dropdown lists and plain tk widgets
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, fieldbackground=FIELD, bordercolor=BORDER,
                darkcolor=BG, lightcolor=BG, troughcolor=FIELD, focuscolor=ACCENT,
                selectbackground=ACCENT, selectforeground="#ffffff", insertcolor=FG, font=FONT)
    s.configure("TFrame", background=BG)
    s.configure("TLabel", background=BG, foreground=FG)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("State.TLabel", font=("Segoe UI", 11, "bold"), foreground=ACCENT_HI)
    s.configure("TLabelframe", background=BG, bordercolor=BORDER, relief="solid")
    s.configure("TLabelframe.Label", background=BG, foreground=ACCENT_HI, font=("Segoe UI", 10, "bold"))

    s.configure("TButton", background=BUTTON, foreground=FG, bordercolor=BORDER, lightcolor=BUTTON,
                darkcolor=BUTTON, padding=(10, 4), relief="flat")
    s.map("TButton",
          background=[("disabled", PANEL), ("pressed", ACCENT), ("active", BUTTON_HI)],
          foreground=[("disabled", DISABLED)],
          lightcolor=[("active", BUTTON_HI)], darkcolor=[("active", BUTTON_HI)])
    s.configure("Accent.TButton", background=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT, foreground="#ffffff")
    s.map("Accent.TButton", background=[("disabled", PANEL), ("pressed", BUTTON_HI), ("active", ACCENT_HI)],
          foreground=[("disabled", DISABLED)])

    s.configure("TEntry", fieldbackground=FIELD, foreground=FG, bordercolor=BORDER,
                lightcolor=BORDER, darkcolor=BORDER, padding=3)
    s.map("TEntry", fieldbackground=[("disabled", PANEL)], foreground=[("disabled", DISABLED)],
          bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])
    s.configure("TCombobox", fieldbackground=FIELD, background=BUTTON, foreground=FG, arrowcolor=FG,
                bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=3)
    s.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)],
          selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", FG)],
          background=[("active", BUTTON_HI)])

    s.configure("Treeview", background=FIELD, fieldbackground=FIELD, foreground=FG, bordercolor=BORDER,
                rowheight=26)
    s.map("Treeview", background=[("selected", BUTTON_HI)], foreground=[("selected", "#ffffff")])
    s.configure("Treeview.Heading", background=PANEL, foreground=ACCENT_HI, bordercolor=BORDER,
                lightcolor=PANEL, darkcolor=PANEL, font=("Segoe UI", 10, "bold"), relief="flat")
    s.map("Treeview.Heading", background=[("active", BUTTON)])

    s.configure("Vertical.TScrollbar", background=BUTTON, troughcolor=FIELD, bordercolor=BG,
                arrowcolor=FG, lightcolor=BUTTON, darkcolor=BUTTON)
    s.map("Vertical.TScrollbar", background=[("active", BUTTON_HI)])
    s.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=FIELD, bordercolor=BORDER,
                lightcolor=ACCENT, darkcolor=ACCENT)
    s.configure("TCheckbutton", background=BG, foreground=FG, indicatorbackground=FIELD,
                indicatorforeground=ACCENT_HI, indicatorcolor=FIELD)
    s.map("TCheckbutton", background=[("active", BG)], indicatorcolor=[("selected", ACCENT)])
    # Cards: panels on the window background
    s.configure("Card.TFrame", background=PANEL)
    s.configure("Card.TLabel", background=PANEL, foreground=FG)
    s.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
    s.configure("CardTitle.TLabel", background=PANEL, foreground=ACCENT_HI, font=("Segoe UI Semibold", 11))
    s.configure("Card.TCheckbutton", background=PANEL, foreground=FG, indicatorbackground=FIELD,
                indicatorforeground=ACCENT_HI, indicatorcolor=FIELD)
    s.map("Card.TCheckbutton", background=[("active", PANEL)], indicatorcolor=[("selected", ACCENT)])
    s.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI Semibold", 17))
    s.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
    s.configure("Thin.Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL, bordercolor=BG,
                lightcolor=ACCENT, darkcolor=ACCENT, thickness=6)
    s.configure("TPanedwindow", background=BG)
    s.configure("Sash", sashthickness=6, gripcount=0, background=BG)


def style_text(widget):
    """Colours for plain tk Text/Listbox widgets, which ttk styles don't reach."""
    widget.configure(bg=FIELD, fg=FG, selectbackground=ACCENT,
                     selectforeground="#ffffff", highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT, relief="flat", borderwidth=0)
    if "insertbackground" in widget.keys():  # Text has a cursor, Listbox does not
        widget.configure(insertbackground=FG)


def dark_titlebar(win):
    """Windows 10/11: dark title bar, and a purple caption on Windows 11."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))  # immersive dark mode
        caption = ctypes.c_int(int(BG[5:7] + BG[3:5] + BG[1:3], 16))               # COLORREF is BGR
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
    except (AttributeError, OSError):
        pass
