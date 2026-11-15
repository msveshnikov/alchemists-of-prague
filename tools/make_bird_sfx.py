"""Synthesised bird sounds for scripts/birds.gd (no recordings, so no licence to track):

  assets/audio/sfx/gull_1..6.wav   herring-gull calls: long call, single "kyow", laughing series, mew, alarm "kek"
  assets/audio/sfx/coo_1..3.wav    rock-pigeon coos ("hu-rroo-oo")
  assets/audio/sfx/wings_1..3.wav  a few pigeons clattering up off the cobbles

Run: python tools/make_bird_sfx.py   (numpy + scipy)
"""
import os
import wave

import numpy as np
from scipy import signal

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio", "sfx")
rnd = np.random.default_rng(5)


def save(name, x, peak=0.85):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", name, f"{len(x) / SR:.2f}s")


def lowpass_noise(n, cutoff):
    b, a = signal.butter(2, cutoff / (SR / 2))
    return signal.lfilter(b, a, rnd.normal(0, 1, n))


def band(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def env_adsr(n, att, rel):
    e = np.ones(n)
    a = max(int(att * SR), 1)
    r = max(int(rel * SR), 1)
    e[:a] = np.linspace(0, 1, a) ** 1.5
    e[-r:] *= np.linspace(1, 0, r) ** 1.2
    return e


def air(x, mix=0.22):
    """Open-air tail: a few sparse, darkening echoes (houses and the river walls)."""
    out = np.concatenate([x, np.zeros(int(0.5 * SR))])
    y = out.copy()
    for d, g in [(0.037, 0.5), (0.071, 0.35), (0.113, 0.28), (0.167, 0.2), (0.23, 0.13), (0.31, 0.08)]:
        k = int(d * SR)
        e = np.zeros_like(out)
        e[k:] = out[:-k]
        b, a = signal.butter(1, 3500 / (SR / 2))
        y += signal.lfilter(b, a, e) * g * mix * 2
    return y


# ----------------------------------------------------------------------------- gull
def formant(f):
    return (1.0 / (1 + (f / 900.0)) ** 0.4 + 1.4 * np.exp(-((f - 1900) / 650) ** 2)
            + 0.9 * np.exp(-((f - 3300) / 900) ** 2) + 0.3 * np.exp(-((f - 4800) / 900) ** 2))


def gull_note(dur, f0, fpk, f1, rough=0.5, peak_at=0.25, bright=1.0):
    n = int(dur * SR)
    x = np.linspace(0, 1, n)
    f = np.where(x < peak_at, f0 + (fpk - f0) * np.sin(x / peak_at * np.pi / 2),
                 fpk + (f1 - fpk) * np.clip((x - peak_at) / (1 - peak_at), 0, 1) ** 1.3)
    f = f * (1 + 0.012 * np.cumsum(rnd.normal(0, 1, n)) / np.sqrt(n) + 0.01 * np.sin(2 * np.pi * 7 * x * dur))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros(n)
    for k in range(1, 16):
        fk = f * k
        y += np.where(fk < SR / 2 - 500, formant(fk) * (1.0 if k == 1 else bright) * np.sin(k * ph), 0.0)
    # raspy voice: fast irregular amplitude and a period-doubling subharmonic
    am = 1 + rough * lowpass_noise(n, 140) / 2.0
    y = y * am + rough * 0.6 * np.sin(0.5 * ph) * np.sin(ph) * formant(f)
    y += band(rnd.normal(0, 1, n), 1800, 4200) * 0.25 * rough
    return y * env_adsr(n, 0.018, min(0.08, dur * 0.4))


def gap(s):
    return np.zeros(int(s * SR))


def gulls():
    calls = []
    # 1: long call "keeee-ow" + a run of "kyow kyow"
    parts = [gull_note(0.55, 850, 1500, 820, 0.45, 0.2), gap(0.12)]
    for i in range(6):
        parts += [gull_note(0.17 + rnd.uniform(-0.02, 0.03), 1000 - i * 25, 1380 - i * 30, 880 - i * 20, 0.55) * (1 - i * 0.08), gap(rnd.uniform(0.07, 0.11))]
    calls.append(np.concatenate(parts))
    # 2: single "kyow"
    calls.append(gull_note(0.32, 950, 1420, 840, 0.5))
    # 3: laughing series
    parts = []
    for i in range(9):
        parts += [gull_note(0.11, 980, 1260 - i * 12, 960, 0.6, 0.3) * (0.7 + 0.3 * np.sin(i / 8 * np.pi)), gap(0.055)]
    calls.append(np.concatenate(parts))
    # 4: plaintive mew
    calls.append(gull_note(0.7, 700, 1050, 880, 0.25, 0.45, 0.6))
    # 5: "kyow - kyow"
    calls.append(np.concatenate([gull_note(0.26, 900, 1450, 820, 0.5), gap(0.16), gull_note(0.28, 880, 1400, 800, 0.55)]))
    # 6: alarm "kek-kek-kek"
    parts = []
    for i in range(5):
        parts += [gull_note(0.075, 1350, 1700, 1400, 0.7, 0.4), gap(0.09)]
    calls.append(np.concatenate(parts))
    for i, c in enumerate(calls):
        save(f"gull_{i + 1}", air(c))


# ----------------------------------------------------------------------------- pigeon
def coo_note(dur, f0, fpk, f1, trill=0.0):
    n = int(dur * SR)
    x = np.linspace(0, 1, n)
    f = np.where(x < 0.4, f0 + (fpk - f0) * np.sin(x / 0.4 * np.pi / 2), fpk + (f1 - fpk) * (x - 0.4) / 0.6)
    f = f * (1 + 0.015 * np.sin(2 * np.pi * 5 * x * dur))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros(n)
    for k, a in enumerate([1.0, 0.45, 0.16, 0.06, 0.025], 1):
        y += a * np.sin(k * ph)
    y += lowpass_noise(n, 700) * 0.6
    if trill:
        tr = 1 - trill * (0.5 + 0.5 * np.sin(2 * np.pi * 27 * x * dur))
        y *= np.where(x < 0.55, tr, 1.0)
    b, a = signal.butter(2, 900 / (SR / 2))
    y = signal.lfilter(b, a, y)
    return y * env_adsr(n, 0.04, min(0.12, dur * 0.4))


def coos():
    for i in range(3):
        k = 1 + rnd.uniform(-0.08, 0.08)
        c = np.concatenate([coo_note(0.13, 300 * k, 350 * k, 320 * k), gap(0.06),
                            coo_note(0.6 + 0.1 * i, 290 * k, 385 * k, 280 * k, 0.6), gap(0.08),
                            coo_note(0.3, 330 * k, 345 * k, 290 * k)])
        if i == 2:
            c = np.concatenate([c, gap(0.25), coo_note(0.5, 300 * k, 380 * k, 285 * k, 0.6)])
        save(f"coo_{i + 1}", air(c, 0.1), 0.7)


# ----------------------------------------------------------------------------- wings
def clap():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    x = rnd.normal(0, 1, n) * np.exp(-t / 0.009)
    return band(x, 700, 5200)


def one_bird(total):
    y = np.zeros(int(total * SR))
    t = rnd.uniform(0.0, 0.12)
    dt = 0.075
    for i in range(rnd.integers(9, 15)):
        c = clap() * rnd.uniform(0.6, 1.0) * (1 - i * 0.045)
        k = int(t * SR)
        if k + len(c) < len(y):
            y[k:k + len(c)] += c
        t += dt * rnd.uniform(0.85, 1.15)
        dt = max(0.055, dt * 0.97)
    # whirr of the wingbeats between the claps
    n = len(y)
    x = np.arange(n) / SR
    wh = band(rnd.normal(0, 1, n), 300, 2200) * (0.5 + 0.5 * np.sin(2 * np.pi * 12 * x)) ** 2
    wh *= np.clip(x / 0.1, 0, 1) * np.clip((total - x) / 0.6, 0, 1) * 0.12
    return y + wh


def wings():
    for i in range(3):
        total = 1.5
        y = np.zeros(int((total + 0.4) * SR))
        for b in range(3 + i * 2):
            o = int(rnd.uniform(0, 0.35) * SR)
            s = one_bird(total) * rnd.uniform(0.5, 1.0)
            y[o:o + len(s)] += s
        save(f"wings_{i + 1}", air(y, 0.1), 0.8)


if __name__ == "__main__":
    gulls()
    coos()
    wings()
