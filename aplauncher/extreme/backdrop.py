"""Animated backdrop rendered with Pillow: purple nebula, drifting particles, scanlines, grain, vignette.

The nebula is computed at a quarter of the window size from two slowly drifting cloud textures and scaled up;
scanlines, vignette and grain are precomputed once per window size and only multiplied in."""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

SCALE = 4


def _clouds(w, h, seed):
    """Soft grey clouds (two octaves of blurred noise), contrast stretched."""
    random.seed(seed)
    out = None
    for div, weight in ((10, 0.65), (4, 0.35)):
        n = Image.effect_noise((max(2, w // div), max(2, h // div)), 90).resize((w, h), Image.BICUBIC)
        n = n.filter(ImageFilter.GaussianBlur(max(1, w // (div * 3))))
        out = n if out is None else Image.blend(out, n, weight)
    out = ImageOps.autocontrast(out, cutoff=2)
    return out.point(lambda v: int(255 * max(0.0, (v - 70) / 185) ** 1.7))


def _sprite(r, color, strength=1.0):
    """Round glowing dot as RGBA."""
    s = r * 4 + 1
    a = Image.new("L", (s, s), 0)
    ImageDraw.Draw(a).ellipse((r, r, s - r - 1, s - r - 1), fill=int(255 * strength))
    a = a.filter(ImageFilter.GaussianBlur(r * 0.7))
    img = Image.new("RGBA", (s, s), color)
    img.putalpha(a)
    return img


class Backdrop:
    def __init__(self, w, h):
        self.particles = []
        self.resize(w, h)

    def resize(self, w, h):
        self.w, self.h = w, h
        sw, sh = max(8, w // SCALE + 1), max(8, h // SCALE + 1)
        self.sw, self.sh = sw, sh
        # Two cloud layers, bigger than the small frame so they can drift.
        self.layers = []
        for seed, dark, mid, light in ((1, (6, 3, 14), (54, 20, 110), (150, 80, 255)),
                                       (2, (4, 2, 10), (80, 18, 92), (215, 110, 255))):
            c = _clouds(int(sw * 1.6), int(sh * 1.6), seed)
            self.layers.append(ImageOps.colorize(c, dark, light, mid=mid, blackpoint=0, whitepoint=255, midpoint=140))
        self.base = Image.new("RGB", (sw, sh), (7, 4, 13))
        # Shade = vignette * scanlines * grain; three grain variants alternate.
        g = Image.radial_gradient("L").resize((w, h), Image.BILINEAR)
        vig = g.point(lambda v: int(255 * (1 - 0.72 * (v / 255) ** 1.8)))
        scan = Image.new("L", (1, h))
        scan.putdata([206 if y % 3 == 0 else 255 for y in range(h)])
        scan = scan.resize((w, h), Image.NEAREST)
        base = ImageChops.multiply(vig, scan)
        self.shades = []
        for i in range(3):
            grain = Image.effect_noise((w, h), 40).point(lambda v: max(0, min(255, 228 + (v - 128) // 3)))
            self.shades.append(Image.merge("RGB", [ImageChops.multiply(base, grain)] * 3))
        # Particles in window coordinates; they keep their place across resizes.
        rnd = random.Random(7)
        if not self.particles:
            for _i in range(46):
                big = rnd.random() < 0.18
                self.particles.append({
                    "x": rnd.random(), "y": rnd.random(), "vy": rnd.uniform(0.004, 0.018) * (0.5 if big else 1),
                    "ph": rnd.uniform(0, 6.3), "amp": rnd.uniform(0.004, 0.02),
                    "spr": _sprite(rnd.choice((5, 7, 9)) if big else rnd.choice((1, 1, 2)),
                                   rnd.choice(((196, 165, 255), (215, 123, 255), (139, 92, 246))),
                                   0.35 if big else 0.9)})
        self.frame_no = 0

    def render(self, t: float) -> Image.Image:
        sw, sh = self.sw, self.sh
        a, b = self.layers
        ax = (a.width - sw) * (0.5 + 0.5 * math.sin(t * 0.045))
        ay = (a.height - sh) * (0.5 + 0.5 * math.sin(t * 0.031 + 1.3))
        bx = (b.width - sw) * (0.5 + 0.5 * math.sin(t * 0.037 + 2.1))
        by = (b.height - sh) * (0.5 + 0.5 * math.cos(t * 0.027))
        ca = a.crop((int(ax), int(ay), int(ax) + sw, int(ay) + sh))
        cb = b.crop((int(bx), int(by), int(bx) + sw, int(by) + sh))
        pulse = 0.55 + 0.12 * math.sin(t * 0.6)
        small = ImageChops.add(self.base, ImageChops.screen(ca, Image.blend(self.base, cb, pulse)))
        frame = small.resize((self.w, self.h), Image.BILINEAR)
        for p in self.particles:
            y = (p["y"] - p["vy"] * t) % 1.08 - 0.04
            x = p["x"] + p["amp"] * math.sin(t * 0.5 + p["ph"])
            s = p["spr"]
            frame.paste(s, (int(x * self.w) - s.width // 2, int(y * self.h) - s.height // 2), s)
        self.frame_no += 1
        return ImageChops.multiply(frame, self.shades[(self.frame_no // 2) % 3])
