"""Colours, fonts and small drawing helpers of the extreme interface."""
import random
import re

from .. import theme

VOID = "#07040d"          # black-violet behind everything
FIELD = "#0f0a1a"         # real widgets (entries, lists, log)
WIRE = "#4b3a80"          # panel outlines at rest
EDGE = theme.GLOW         # print edge, wireframe while building
FG, MUTED, ACCENT, ACCENT_HI = theme.FG, theme.MUTED, theme.ACCENT, theme.ACCENT_HI
OK, WARN, ERR, GLOW, PINK = theme.OK, theme.WARN, theme.ERR, theme.GLOW, theme.PINK

HEAD = "Bahnschrift"
F_TITLE = (HEAD, 24, "bold")
F_PANEL = ("Bahnschrift SemiBold", 10)
F_BUTTON = ("Bahnschrift SemiBold", 10)
F_TAB = ("Bahnschrift SemiBold", 11)
F_BODY = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)
F_LABEL = ("Bahnschrift", 9)
F_MONO = ("Consolas", 9)

GLYPHS = "▓▒░█<>/\\|#%&@$*+=_01ABCDEFXYZ"


def scramble(text: str, p: float, spread=1.6) -> str:
    """Text at reveal progress p: settled characters on the left, random glyphs in front of them."""
    n = len(text)
    if p >= 1 or n == 0:
        return text
    done = int(n * p)
    shown = min(n, int(n * p * spread) + 1)
    return text[:done] + "".join(c if c == " " else random.choice(GLYPHS) for c in text[done:shown])


_EMOJI = re.compile(r"^[^\w(\"'„]+")


def plain(text: str) -> str:
    """Button texts of the clean interface start with an emoji; the extreme look uses plain words."""
    return _EMOJI.sub("", text).strip()


def chamfer(x, y, w, h, k=12):
    """Rectangle with the top-left and bottom-right corners cut off (flat list for canvas polygons)."""
    return [x + k, y, x + w, y, x + w, y + h - k, x + w - k, y + h, x, y + h, x, y + k]


def chamfer_points(x, y, w, h, k=12):
    p = chamfer(x, y, w, h, k)
    return list(zip(p[0::2], p[1::2]))


def path_part(points, frac, closed=True):
    """The first frac of the outline through points (flat list), to draw a line that grows."""
    pts = points + [points[0]] if closed else list(points)
    segs = [((ax, ay), (bx, by), ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5)
            for (ax, ay), (bx, by) in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs)
    left = max(0.0, min(1.0, frac)) * total
    out = [pts[0][0], pts[0][1]]
    for (ax, ay), (bx, by), ln in segs:
        if left >= ln:
            out += [bx, by]
            left -= ln
        else:
            t = left / ln if ln else 0
            out += [ax + (bx - ax) * t, ay + (by - ay) * t]
            break
    if len(out) < 4:
        out += out
    return out


def point_at(points, frac):
    """Position at frac of the closed outline."""
    p = path_part(points, frac)
    return p[-2], p[-1]
