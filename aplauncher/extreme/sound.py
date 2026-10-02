"""Interface sounds, synthesised in code (no sound files ship with the launcher).

winsound cannot play from memory asynchronously, so the sounds are written once as WAV files to
%APPDATA%\\APLauncher\\sounds and played from there. winsound plays one sound at a time; the intro is
therefore one premixed track that matches the build-up timeline."""
import array
import math
import os
import random
import threading
import wave
import winsound
from pathlib import Path

RATE = 22050
VERSION = 1


def _dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "APLauncher" / "sounds"


class _Track:
    def __init__(self, seconds):
        self.buf = [0.0] * int(seconds * RATE)

    def add(self, start, samples):
        i0 = int(start * RATE)
        buf = self.buf
        for i, v in enumerate(samples, i0):
            if 0 <= i < len(buf):
                buf[i] += v

    def save(self, path, gain=0.8):
        peak = max(1e-6, max(abs(v) for v in self.buf))
        k = gain / peak * 32767
        data = array.array("h", (int(v * k) for v in self.buf))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(data.tobytes())


def _env(n, attack, release):
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    for i in range(n):
        yield min(1.0, i / a) * min(1.0, (n - i) / r)


def tone(sec, f0, f1=None, amp=1.0, attack=0.005, release=0.05, shape="sine"):
    f1 = f0 if f1 is None else f1
    n = int(sec * RATE)
    ph = 0.0
    out = []
    for i, e in enumerate(_env(n, attack, release)):
        f = f0 + (f1 - f0) * i / n
        ph += 2 * math.pi * f / RATE
        if shape == "sine":
            v = math.sin(ph)
        elif shape == "tri":
            v = 2 / math.pi * math.asin(math.sin(ph))
        else:  # soft square
            v = math.tanh(3 * math.sin(ph))
        out.append(v * e * amp)
    return out


def noise(sec, amp=1.0, cut0=0.05, cut1=0.05, attack=0.01, release=0.1):
    """Low-passed noise with a sweeping cutoff (one-pole filter, cut = 0..1)."""
    n = int(sec * RATE)
    y = 0.0
    out = []
    for i, e in enumerate(_env(n, attack, release)):
        a = cut0 + (cut1 - cut0) * i / n
        y += a * (random.uniform(-1, 1) - y)
        out.append(y * e * amp * 3)
    return out


def click(amp=0.5):
    return [random.uniform(-1, 1) * amp * (1 - i / 90) for i in range(90)]


def _intro(path):
    t = _Track(3.1)
    t.add(0.0, noise(0.6, 0.5, 0.02, 0.35, 0.05, 0.3))                 # scan wipe whoosh
    t.add(0.0, tone(2.9, 55, 82, 0.35, 0.4, 0.8, "tri"))               # low hum rising
    t.add(0.45, tone(0.9, 880, 880, 0.25, 0.002, 0.85))                # light ring ping
    t.add(0.47, tone(0.8, 1320, 1320, 0.12, 0.002, 0.75))
    for i in range(16):                                                 # particles snapping onto edges
        t.add(0.55 + i * 0.055 + random.uniform(0, 0.03), click(0.45))
    t.add(0.95, [v * (0.5 + 0.5 * math.sin(i / RATE * 2 * math.pi * 14))
                 for i, v in enumerate(tone(1.2, 196, 196, 0.10, 0.05, 0.2, "square"))])  # printer buzz
    for i, f in enumerate((1568, 1760, 2093, 1760, 2349)):              # buttons flashing up
        t.add(1.45 + i * 0.13, tone(0.12, f, f, 0.12, 0.002, 0.1))
    for f in (220, 330, 440, 554):                                     # settle chord
        t.add(2.3, tone(0.8, f, f, 0.12, 0.08, 0.6, "tri"))
    t.save(path)


def _glitch(path):
    t = _Track(0.3)
    for i in range(6):
        t.add(i * 0.045, noise(0.03, 0.6, 0.6, 0.6, 0.001, 0.01))
    t.add(0.0, tone(0.25, 900, 120, 0.2, 0.002, 0.1, "square"))
    t.save(path, 0.6)


def _banner(path):
    t = _Track(0.9)
    t.add(0.0, noise(0.25, 0.4, 0.05, 0.4, 0.01, 0.2))
    t.add(0.05, tone(0.18, 660, 660, 0.3, 0.003, 0.08, "tri"))
    t.add(0.18, tone(0.6, 990, 990, 0.3, 0.003, 0.5, "tri"))
    t.add(0.18, tone(0.6, 1485, 1485, 0.1, 0.003, 0.5))
    t.save(path)


def _click(path):
    t = _Track(0.06)
    t.add(0.0, tone(0.05, 1800, 900, 0.5, 0.001, 0.04))
    t.save(path, 0.5)


MAKERS = {"intro": _intro, "glitch": _glitch, "banner": _banner, "click": _click}


class Sounds:
    def __init__(self, enabled):
        self.enabled = enabled
        self.ready = False
        threading.Thread(target=self._prepare, daemon=True).start()

    def _path(self, name):
        return _dir() / f"{name}_v{VERSION}.wav"

    def _prepare(self):
        try:
            _dir().mkdir(parents=True, exist_ok=True)
            for name, make in MAKERS.items():
                if not self._path(name).is_file():
                    make(self._path(name))
            self.ready = True
        except OSError:
            pass

    def play(self, name):
        if not (self.enabled and self.ready):
            return
        try:
            winsound.PlaySound(str(self._path(name)), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except RuntimeError:
            pass
