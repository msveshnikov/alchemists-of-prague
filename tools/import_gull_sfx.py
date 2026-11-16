"""Clean up recorded gull calls and install them as assets/audio/sfx/gull_N.wav (mono, for 3D playback).

Source: "Solo Seagull Sound Effects" by Rango Mango, CC0, https://opengameart.org/content/solo-seagull-sound-effects
(the "Seagull Ambient 1..7" and "Seagull Big Ambient (2)" WAVs). Download them into a folder, then:

    python tools/import_gull_sfx.py <folder>

Processing: mono, 300 Hz high-pass, spectral noise gate (profile from the quietest frames), trim, fades, normalise.
"""
import glob
import os
import sys
import wave

import numpy as np
from scipy import signal

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio", "sfx")
# whole files; Ambient 2/3/7 and Big Ambient are too quiet or noisy after cleaning and are not used
ORDER = ["Seagull_Ambient_1", "Seagull_Big_Ambient_2", "Seagull_Ambient_4", "Seagull_Ambient_5", "Seagull_Ambient_6"]
SPLIT = "Seagull_Big_Ambient_2"     # its separate calls also become short single-call variants


def load(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).astype(np.float64)
    return x.mean(1) / 32768.0, w.getframerate()


def clean(x, sr):
    b, a = signal.butter(4, 300 / (sr / 2), "high")
    x = signal.filtfilt(b, a, x)
    f, t, Z = signal.stft(x, sr, nperseg=1024, noverlap=768)
    mag = np.abs(Z)
    energy = mag.sum(0)
    quiet = energy <= np.percentile(energy, 15)
    noise = mag[:, quiet].mean(1, keepdims=True)
    gain = np.clip((mag - 2.2 * noise) / np.maximum(mag, 1e-12), 0.0, 1.0)
    gain = signal.convolve2d(gain, np.ones((3, 5)) / 15.0, mode="same")      # smooth: no musical noise
    _, y = signal.istft(Z * gain, sr, nperseg=1024, noverlap=768)
    # trim to the calls
    env = np.convolve(np.abs(y), np.ones(int(0.02 * sr)) / (0.02 * sr), mode="same")
    on = np.where(env > env.max() * 0.04)[0]
    pad = int(0.05 * sr)
    y = y[max(on[0] - pad, 0):min(on[-1] + 4 * pad, len(y))]
    fi, fo = int(0.01 * sr), int(0.12 * sr)
    y[:fi] *= np.linspace(0, 1, fi)
    y[-fo:] *= np.linspace(1, 0, fo)
    return y / (np.abs(y).max() + 1e-9) * 0.85


def calls(y, sr, min_gap=0.12, min_len=0.25):
    """Cut a cleaned series into separate calls at the silent gaps."""
    env = np.convolve(np.abs(y), np.ones(int(0.015 * sr)) / (0.015 * sr), mode="same")
    loud = env > env.max() * 0.06
    segs, start, quiet = [], None, 0
    for i, v in enumerate(loud):
        if v:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet > min_gap * sr:
                segs.append((start, i - quiet))
                start = None
    if start is not None:
        segs.append((start, len(y)))
    out = []
    for a, b in segs:
        if (b - a) / sr >= min_len:
            c = y[max(a - int(0.03 * sr), 0):min(b + int(0.15 * sr), len(y))].copy()
            fo = min(int(0.1 * sr), len(c) // 3)
            c[-fo:] *= np.linspace(1, 0, fo)
            out.append(c / (np.abs(c).max() + 1e-9) * 0.85)
    return out


def save(path, y, sr):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())


def main(src):
    files = {os.path.splitext(os.path.basename(p))[0].replace(" ", "_"): p for p in glob.glob(os.path.join(src, "*.wav"))}
    for old in glob.glob(os.path.join(OUT, "gull_*.wav")):
        os.remove(old)
        if os.path.exists(old + ".import"):
            os.remove(old + ".import")
    for i, name in enumerate(ORDER, 1):
        x, sr = load(files[name])
        y = clean(x, sr)
        save(os.path.join(OUT, f"gull_{i}.wav"), y, sr)
        print(f"gull_{i}.wav <- {name}  {len(y) / sr:.2f}s")
    x, sr = load(files[SPLIT])
    n = len(ORDER)
    for c in calls(clean(x, sr), sr)[:5]:
        n += 1
        save(os.path.join(OUT, f"gull_{n}.wav"), c, sr)
        print(f"gull_{n}.wav <- {SPLIT} (one call)  {len(c) / sr:.2f}s")


if __name__ == "__main__":
    main(sys.argv[1])
