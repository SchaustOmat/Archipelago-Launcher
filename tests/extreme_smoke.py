"""Smoke test of the extreme interface: build-up, tab changes, item banner, frame times, idle CPU.

Settings are copied to a temp file, so the real launcher settings stay untouched. Screenshots of every phase go
to the folder given as first argument (default: temp). Run: python tests/extreme_smoke.py [out_dir]
"""
import ctypes
import json
import shutil
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image

from aplauncher import config

out = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="aplauncher_xshots_"))
out.mkdir(parents=True, exist_ok=True)
scratch = Path(tempfile.mkdtemp(prefix="aplauncher_xtest_"))
real = config.settings_path()
fake = scratch / "settings.json"
if real.is_file():
    shutil.copy(real, fake)
s = json.loads(fake.read_text(encoding="utf-8")) if fake.is_file() else {}
s.update(ui_style="extreme", intro=True)
fake.write_text(json.dumps(s), encoding="utf-8")
config.settings_path = lambda: fake

from aplauncher.extreme.app import ExtremeApp  # noqa: E402

app = ExtremeApp()
root = app.root
t_start = time.perf_counter()
shots = []


def capture(hwnd):
    """Window contents via PrintWindow, also when other windows cover it."""
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    for fn, res, args in ((user32.GetWindowDC, ctypes.c_void_p, [ctypes.c_void_p]),
                          (gdi32.CreateCompatibleDC, ctypes.c_void_p, [ctypes.c_void_p]),
                          (gdi32.CreateCompatibleBitmap, ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]),
                          (gdi32.SelectObject, ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]),
                          (user32.PrintWindow, ctypes.c_int, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]),
                          (gdi32.GetDIBits, ctypes.c_int, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                                           ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]),
                          (gdi32.DeleteObject, ctypes.c_int, [ctypes.c_void_p]),
                          (gdi32.DeleteDC, ctypes.c_int, [ctypes.c_void_p]),
                          (user32.ReleaseDC, ctypes.c_int, [ctypes.c_void_p, ctypes.c_void_p])):
        fn.restype, fn.argtypes = res, args
    rect = wintypes.RECT()
    user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT

    class BMI(ctypes.Structure):
        _fields_ = [("size", ctypes.c_uint32), ("w", ctypes.c_int32), ("h", ctypes.c_int32), ("planes", ctypes.c_uint16),
                    ("bits", ctypes.c_uint16), ("comp", ctypes.c_uint32), ("img", ctypes.c_uint32),
                    ("xp", ctypes.c_int32), ("yp", ctypes.c_int32), ("used", ctypes.c_uint32), ("imp", ctypes.c_uint32)]
    bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1)


def grab(name):
    root.update_idletasks()
    img = capture(ctypes.windll.user32.GetParent(root.winfo_id()))
    path = out / f"{len(shots):02d}_{name}.png"
    img.save(path)
    shots.append(path)


def at(ms, fn):
    root.after(ms, fn)


app.sc.keep_running = True  # the test must not steal the focus; animate as if focused
for ms in (120, 330, 620, 950, 1300, 1700, 2200, 3300):
    at(ms, lambda ms=ms: grab(f"intro_{ms}"))
at(3600, lambda: app.tabs.select("setup"))
at(3660, lambda: grab("setup_glitch"))
at(3900, lambda: grab("setup_build"))
at(4700, lambda: grab("setup"))
at(5000, lambda: app.tabs.select("net"))
at(5900, lambda: grab("net"))
at(6100, lambda: app.tabs.select("log"))
at(7000, lambda: grab("log"))
at(7200, lambda: app.tabs.select("play"))
at(8200, lambda: app._watch_event("received", {"item": "Hookshot", "sender": "Link", "progression": True}))
at(8800, lambda: grab("banner"))
cpu = {}


def cpu_start():
    app.sc.frame_ms.clear()
    cpu["t"], cpu["p"] = time.perf_counter(), time.process_time()


def cpu_end():
    wall = time.perf_counter() - cpu["t"]
    proc = time.process_time() - cpu["p"]
    fm = sorted(app.sc.frame_ms)
    print(f"idle CPU: {proc / wall * 100:.1f} % of one core over {wall:.1f}s")
    if fm:
        print(f"compose ms: median {fm[len(fm) // 2]:.1f}, p95 {fm[int(len(fm) * .95)]:.1f}, frames {len(fm)}")
    root.after(100, lambda: app.on_close(ask=False))


at(14000, cpu_start)
at(19000, cpu_end)
app.run()
print("screenshots:", out)
for p in shots:
    print(" ", p.name)
