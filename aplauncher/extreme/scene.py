"""The window as one canvas: backdrop and glass panels are composed with Pillow into a single image, everything
else is canvas items on top. Real tk widgets sit in canvas windows."""
import random
import time
import tkinter as tk

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

from .. import anim
from . import look
from .backdrop import Backdrop

AMBIENT_FPS = 6       # backdrop when nothing else moves (it drifts slowly)
BOOST_FPS = 60        # while building up / glitching
GLASS_EVERY = 1.0     # seconds between new blur snapshots
GLASS_FADE = 0.4      # cross-fade between two snapshots


class Timeline:
    """Tweens of one build-up; finish() jumps all of them to their end (skip)."""

    def __init__(self, canvas):
        self.c = canvas
        self.tweens = []

    def add(self, delay, ms, update, ease=anim.linear, done=None):
        tw = anim.Tween(self.c, ms, update, ease=ease, done=done, delay=delay)
        self.tweens.append(tw)
        return tw

    def at(self, delay, fn):
        return self.add(delay, 1, lambda t: None, done=fn)

    def end_ms(self):
        now = time.perf_counter()
        return max([(tw.t0 - now) * 1000 + tw.ms for tw in self.tweens if tw.active] or [0])

    def running(self):
        self.tweens = [tw for tw in self.tweens if tw.active]
        return bool(self.tweens)

    def finish(self):
        # Tweens started by a done() callback land in self.tweens too, so repeat until nothing is left.
        for _i in range(6):
            pending = [tw for tw in self.tweens if tw.active]
            self.tweens = []
            if not pending:
                return
            for tw in sorted(pending, key=lambda tw: tw.t0):
                tw.cancel()
                tw.update(tw.ease(1.0))
                if tw.done:
                    tw.done()


class Glass:
    """Frosted glass panel: blurred snapshot of the backdrop underneath, tinted, with a sheen."""

    def __init__(self, x, y, w, h, k=14):
        self.x, self.y, self.w, self.h, self.k = int(x), int(y), max(8, int(w)), max(8, int(h)), k
        self.mask = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(self.mask).polygon(look.chamfer(0, 0, self.w - 1, self.h - 1, k), fill=255)
        tint = Image.new("RGB", (self.w, self.h), (22, 14, 40))
        sheen = Image.linear_gradient("L").rotate(180).resize((self.w, self.h)).point(lambda v: int(v * 0.10))
        self.tint = ImageChops.add(tint, Image.merge("RGB", (sheen, sheen, sheen)))
        self.img = self.prev = None
        self.t_snap = -1.0
        self.reveal = 0.0

    def snapshot(self, frame, now):
        box = (self.x, self.y, self.x + self.w, self.y + self.h)
        crop = frame.crop(box)
        small = crop.resize((max(2, self.w // 6), max(2, self.h // 6)), Image.BILINEAR)
        blur = small.filter(ImageFilter.GaussianBlur(2)).resize((self.w, self.h), Image.BILINEAR)
        new = Image.blend(blur, self.tint, 0.58)
        if self.img is not None:
            self.prev = self.current(now)
        self.img, self.t_snap = new, now

    def current(self, now):
        a = (now - self.t_snap) / GLASS_FADE
        if self.prev is None or a >= 1:
            self.prev = None
            return self.img
        return Image.blend(self.prev, self.img, max(0.0, a))

    def paste_into(self, frame, now):
        if self.reveal <= 0 or self.img is None:
            return
        mask = self.mask
        if self.reveal < 1:
            mask = mask.copy()
            edge = int(self.h * self.reveal) // 3 * 3  # whole "print lines"
            ImageDraw.Draw(mask).rectangle((0, edge, self.w, self.h), fill=0)
        frame.paste(self.current(now), (self.x, self.y), mask)


class Scene:
    def __init__(self, root, w, h):
        self.root = root
        self.c = tk.Canvas(root, highlightthickness=0, bd=0, bg=look.VOID, width=w, height=h)
        self.c.pack(fill="both", expand=True)
        self.w, self.h = w, h
        self.backdrop = Backdrop(self.w, self.h)
        self.photo = ImageTk.PhotoImage(Image.new("RGB", (self.w, self.h), look.VOID))
        self.bg = self.c.create_image(0, 0, image=self.photo, anchor="nw")
        self.elems = []
        self.page = None
        self.glasses = {}        # page key -> list of Glass (None = always visible)
        self.wipe = 1.0          # fraction of the window revealed by the scan line
        self.boost_until = 0.0
        self.t0 = time.perf_counter()
        self.last = 0.0
        self.last_frame = None
        self.on_layout = None
        self.hooks = []          # fn(now) called on every composed frame (pulsing dots etc.)
        self.frame_ms = []       # last compose durations, for the smoke test
        self.sound = lambda name: None
        self.keep_running = False  # tests: animate even without focus
        self.animate_bg = True     # False: the backdrop stands still between build-ups (cheap, remote-desktop friendly)
        self._resize_job = None
        self.loop = anim.Loop(self.c, self._tick, fps=AMBIENT_FPS, ambient=True)
        self.c.bind("<Configure>", self._configure)

    # ----- elements and pages -----
    def add(self, elem):
        self.elems.append(elem)

    def page_visible(self, page):
        return page is None or page == self.page

    def show_page(self, page):
        self.page = page
        for e in self.elems:
            e.sync()

    def glass_for(self, page):
        return self.glasses.get(None, []) + (self.glasses.get(page, []) if page else [])

    # ----- frame clock -----
    def boost(self, ms):
        """Full frame rate for a while (build-up, glitches)."""
        self.boost_until = max(self.boost_until, time.perf_counter() + ms / 1000)
        self.loop.fps = BOOST_FPS
        self.loop.ambient = False
        self.loop.hidden = False
        self.loop.start()

    def _tick(self, _t):
        now = time.perf_counter()
        boosted = now < self.boost_until
        if not boosted and self.loop.fps != AMBIENT_FPS:
            self.loop.fps = AMBIENT_FPS
        self.loop.ambient = not (boosted or self.keep_running)
        # The engine ticks as fast as the fastest animation needs; the backdrop keeps its own pace.
        if now - self.last < 1 / (BOOST_FPS if boosted else AMBIENT_FPS) - 0.002:
            return
        if not boosted and not self.animate_bg and self.last_frame is not None:
            if all(g.prev is None and g.img is not None for g in self.glass_for(self.page)):
                return
        self.last = now
        self.compose(now)

    def compose(self, now=None):
        now = time.perf_counter() if now is None else now
        t0 = time.perf_counter()
        frame = self.backdrop.render(now - self.t0)
        glasses = self.glass_for(self.page)
        for g in glasses:
            if g.reveal > 0 and (g.img is None or now - g.t_snap > GLASS_EVERY):
                g.snapshot(frame, now)
        for g in glasses:
            g.paste_into(frame, now)
        if self.wipe < 1:
            y = int(self.h * self.wipe)
            frame.paste(look.VOID, (0, y, self.w, self.h))
        self.last_frame = frame
        self.photo.paste(frame)
        for fn in list(self.hooks):
            fn(now)
        self.frame_ms = (self.frame_ms + [(time.perf_counter() - t0) * 1000])[-120:]

    # ----- resizing -----
    def _configure(self, e):
        if (e.width, e.height) == (self.w, self.h) or e.width < 50:
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(90, lambda: self._resize(e.width, e.height))

    def _resize(self, w, h):
        self._resize_job = None
        self.w, self.h = w, h
        self.backdrop.resize(w, h)
        self.photo = ImageTk.PhotoImage(Image.new("RGB", (w, h), look.VOID))
        self.c.itemconfigure(self.bg, image=self.photo)
        if self.on_layout:
            self.on_layout(w, h)
        self.compose()

    # ----- glitch -----
    def glitch(self, ms=230):
        """Tear the current picture into RGB-split bands that jitter and vanish."""
        frame = self.last_frame
        if frame is None:
            return
        self.boost(ms + 100)
        r, g, b = frame.split()
        shift = Image.merge("RGB", (ImageChops.offset(r, 7, 0), g, ImageChops.offset(b, -7, 0)))
        bands = []
        y = random.randint(0, 20)
        while y < self.h:
            bh = random.randint(10, 54)
            if random.random() < 0.75:
                img = ImageTk.PhotoImage(shift.crop((0, y, self.w, min(self.h, y + bh))))
                bands.append((self.c.create_image(0, y, image=img, anchor="nw", tags=("fx",)), img, y,
                              random.uniform(0.35, 1.0)))
            y += bh + random.randint(2, 40)
        state = {"next": 0.0}

        def jitter(t):
            if t < state["next"]:  # new offsets about every 30 ms, not on every frame
                return
            state["next"] = t + 30 / ms
            for item, _img, by, gone in bands:
                if t > gone:
                    self.c.itemconfigure(item, state="hidden")
                else:
                    self.c.coords(item, random.randint(-40, 40) * (1 - t * 0.6), by)

        def done():
            for item, _img, _y, _g in bands:
                self.c.delete(item)
        anim.Tween(self.c, ms, jitter, done=done)
        return [b[0] for b in bands]
