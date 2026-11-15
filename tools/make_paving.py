"""Paving textures for the world-space paving shader (assets/shaders/paving.gdshader).

  paving_cobble.png / _n.png  rounded field-stone cobbles ("cat heads") of mixed granite, basalt and sandstone,
                              irregular sizes, sand and moss in the joints: Old Town Square and the streets
  paving_setts.png / _n.png   rectangular granite setts laid in rows across the bridge, worn flat: Charles Bridge
  paving_macro.png            low-frequency world noise: R dirt, G puddles, B hue drift (breaks up the repeat)

Albedo PNGs carry the height in alpha (1 = stone top, 0 = bottom of the joint), the shader uses it for
parallax occlusion, puddles and roughness. Normal maps keep only X/Y (Godot imports them as RGTC).
Everything tiles seamlessly; one albedo/normal repeat covers TILE_M metres (the shader uniform tile_m).

Run: python tools/make_paving.py      (numpy + Pillow, ~1 min)
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "textures")
SIZE = 2048
TILE_M = 4.0


# ----------------------------------------------------------------------------- noise
def value_noise(size, cells, rnd):
    g = rnd.random((cells, cells)).astype(np.float32)
    u = np.arange(size, dtype=np.float32) * cells / size
    i0 = np.floor(u).astype(int)
    f = u - i0
    f = f * f * (3 - 2 * f)
    i0 %= cells
    i1 = (i0 + 1) % cells
    a, b = g[i0][:, i0], g[i0][:, i1]
    c, d = g[i1][:, i0], g[i1][:, i1]
    fx, fy = f[None, :], f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(size, cells, octaves, seed, pers=0.5):
    rnd = np.random.default_rng(seed)
    tot = np.zeros((size, size), np.float32)
    amp = norm = 0.0
    amp = 1.0
    for o in range(octaves):
        c = cells * 2 ** o
        if c > size:
            break
        tot += value_noise(size, c, rnd) * amp
        norm += amp
        amp *= pers
    return tot / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hexc(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def normal_xy(h, strength):
    """Tileable normal from height; returns RGB uint8 with X/Y in R/G (B = Z for previews)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny, nz = -dx * strength, -dy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], -1)
    return (np.clip(n * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)


def blur(a, r):
    """Cheap tileable box blur (3 passes ~ gaussian)."""
    for _ in range(3):
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, 0)
        a = acc / (2 * r + 1)
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, 1)
        a = acc / (2 * r + 1)
    return a


def save(name, rgb, alpha=None):
    arr = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alpha is not None:
        a = (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)
        arr = np.concatenate([arr, a[..., None]], -1)
        Image.fromarray(arr, "RGBA").save(os.path.join(OUT, name + ".png"), optimize=True)
    else:
        Image.fromarray(arr, "RGB").save(os.path.join(OUT, name + ".png"), optimize=True)
    print("wrote", name)


# ----------------------------------------------------------------------------- stone colours
GRANITE = ["#8a8580", "#76726e", "#9a948b", "#6b6862", "#a39b8e"]
BASALT = ["#4f5257", "#5d6066", "#464a50"]
SAND = ["#a08a6c", "#8f7759", "#b09878", "#9a7f63"]
RUST = ["#8a6a52", "#7c5d48"]


def stone_palette(rnd, n, mix=(0.5, 0.2, 0.22, 0.08)):
    fam = rnd.choice(4, n, p=np.array(mix) / sum(mix))
    cols = np.zeros((n, 3), np.float32)
    for i in range(n):
        lst = (GRANITE, BASALT, SAND, RUST)[fam[i]]
        c = hexc(lst[rnd.integers(len(lst))])
        cols[i] = c * rnd.uniform(0.8, 1.12) + rnd.normal(0, 0.008, 3)
    return cols, fam


# ----------------------------------------------------------------------------- cobbles
def cobbles(seed=7):
    rnd = np.random.default_rng(seed)
    G = 27                                     # stones per tile edge -> ~15 cm stones on a 4 m tile
    n = G * G
    gy, gx = np.mgrid[0:G, 0:G]
    pts = (np.stack([gx.ravel(), gy.ravel()], 1) + 0.5 + rnd.uniform(-0.42, 0.42, (n, 2))) / G
    # a few Lloyd-like relax passes on the torus keep the stones roundish but irregular
    w = rnd.normal(0.0, 1.0, n) * 0.12 / G ** 2   # power-diagram weights: stones of different size
    big = rnd.random(n) < 0.07
    w[big] += 0.5 / G ** 2
    KS = 0.0075
    rad = np.full(n, 0.5 / G)
    cols, fam = stone_palette(rnd, n)
    hoff = rnd.uniform(-0.12, 0.08, n)            # some stones sit higher or sunk
    tilt = rnd.normal(0, 0.9, (n, 2))             # each stone slightly tilted
    sat = rnd.uniform(0.35, 0.8, n)

    H = np.zeros((SIZE, SIZE), np.float32)
    ALB = np.zeros((SIZE, SIZE, 3), np.float32)
    EDGE = np.zeros((SIZE, SIZE), np.float32)
    ID = np.zeros((SIZE, SIZE), np.int32)
    grain = fbm(SIZE, 256, 2, seed + 1)
    grain2 = fbm(SIZE, 128, 3, seed + 2)
    pit = fbm(SIZE, 64, 4, seed + 3)
    gapn = fbm(SIZE, 24, 4, seed + 4)
    xs = (np.arange(SIZE, dtype=np.float32) + 0.5) / SIZE
    CH = 128
    off = [(i, j) for i in range(-2, 3) for j in range(-2, 3)]
    for y0 in range(0, SIZE, CH):
        ys = (np.arange(y0, y0 + CH, dtype=np.float32) + 0.5) / SIZE
        PX, PY = np.meshgrid(xs, ys)
        cx = np.floor(PX * G).astype(int)
        cy = np.floor(PY * G).astype(int)
        cand_p, cand_x, cand_y, cand_i = [], [], [], []
        for (oi, oj) in off:
            ix, iy = cx + oi, cy + oj
            wx, wy = np.floor_divide(ix, G), np.floor_divide(iy, G)
            idx = (iy % G) * G + (ix % G)
            sx = pts[idx, 0] + wx
            sy = pts[idx, 1] + wy
            d2 = (PX - sx) ** 2 + (PY - sy) ** 2
            cand_p.append(d2 - w[idx])
            cand_x.append(sx)
            cand_y.append(sy)
            cand_i.append(idx)
        P = np.stack(cand_p)
        CX, CY, CI = np.stack(cand_x), np.stack(cand_y), np.stack(cand_i)
        k = np.argmin(P, 0)
        sel = lambda A: np.take_along_axis(A, k[None], 0)[0]
        pi, sx, sy, si = sel(P), sel(CX), sel(CY), sel(CI)
        # exact distance to the power-diagram border
        # soft minimum over the borders rounds the stone corners (wider sandy joints where three stones meet)
        acc = np.zeros(PX.shape, np.float32)
        for j in range(len(off)):
            dd = np.sqrt((CX[j] - sx) ** 2 + (CY[j] - sy) ** 2)
            ok = dd > 1e-6
            e = (P[j] - pi) / (2 * np.where(ok, dd, 1.0)) * TILE_M
            acc += np.where(ok, np.exp(-np.clip(e, 0, 1) / KS), 0.0)
        e_m = -KS * np.log(np.maximum(acc, 1e-30))   # metres to the (rounded) joint centre
        r = rad[si] * TILE_M
        ID[y0:y0 + CH] = si
        EDGE[y0:y0 + CH] = e_m
        # rounded dome: steep shoulders near the joint, gentle crown
        gw = 0.0025 + 0.006 * gapn[y0:y0 + CH]   # half joint width, m
        t = np.clip((e_m - gw) / (0.55 * r), 0, 1)
        shoulder = np.sqrt(1 - (1 - t) ** 2)
        dcx = (PX - sx) * TILE_M
        dcy = (PY - sy) * TILE_M
        crown = np.clip(1 - (dcx ** 2 + dcy ** 2) / (1.6 * r) ** 2, 0, 1)
        h = 0.62 * shoulder + 0.3 * crown * shoulder + hoff[si] * shoulder
        h += (tilt[si, 0] * dcx + tilt[si, 1] * dcy) * shoulder
        rough = (pit[y0:y0 + CH] - 0.5) * 0.12 + (grain2[y0:y0 + CH] - 0.5) * 0.05
        h += rough * shoulder
        h = np.where(e_m < gw, 0.0, h)
        H[y0:y0 + CH] = h
        # colour: granite grain flecks, darker shoulders (AO), polished lighter crowns
        base = cols[si]
        g = grain[y0:y0 + CH][..., None]
        speck = (g - 0.5) * np.where(fam[si] == 0, 0.55, 0.25)[..., None]
        c = base * (1 + speck) + (grain2[y0:y0 + CH][..., None] - 0.5) * 0.12
        lum = c.mean(-1, keepdims=True)
        c = lum + (c - lum) * sat[si][..., None]
        c *= (0.55 + 0.45 * shoulder[..., None]) * (0.92 + 0.16 * crown[..., None])
        ALB[y0:y0 + CH] = c
    # joints: sand, soil and moss
    H = np.clip(H, 0, 1.15) / 1.15
    soil = np.stack([fbm(SIZE, 16, 5, seed + 9)] * 3, -1)
    sand = np.array([0.42, 0.36, 0.28]) * (0.8 + 0.4 * soil) * (0.9 + 0.25 * (grain[..., None] - 0.5))
    dark = np.array([0.17, 0.14, 0.11])
    moss_m = smoothstep(0.55, 0.75, fbm(SIZE, 8, 5, seed + 11))
    moss = np.array([0.23, 0.27, 0.12]) * (0.8 + 0.5 * grain[..., None])
    fill = smoothstep(0.0, 0.18, gapn)[..., None]           # sand-filled joints vs deep dark ones
    joint = dark * (1 - fill) + sand * fill
    joint = joint * (1 - moss_m[..., None]) + moss * moss_m[..., None]
    jm = smoothstep(0.02, 0.16, H)[..., None]
    ALB = joint * (1 - jm) + ALB * jm
    # moss creeping on to the stone feet
    creep = (moss_m * (1 - smoothstep(0.1, 0.35, H)))[..., None] * 0.7
    ALB = ALB * (1 - creep) + moss * creep
    # cavity AO from blurred height
    cav = np.clip(H - blur(H, 6), -0.3, 0.3)
    ALB *= (1 + cav * 0.9)[..., None]
    ALB *= (0.9 + 0.15 * fbm(SIZE, 4, 4, seed + 13))[..., None]
    # joint height: sand fills low
    H = np.maximum(H, 0.08 * fill[..., 0] * (0.7 + 0.6 * soil[..., 0]))
    save("paving_cobble", ALB, H)
    Image.fromarray(normal_xy(H, 9.0), "RGB").save(os.path.join(OUT, "paving_cobble_n.png"), optimize=True)
    print("wrote paving_cobble_n")


# ----------------------------------------------------------------------------- setts (bridge)
def setts(seed=21):
    """Rows run along texture Y (world Z, across the bridge), rows follow each other along X (along the bridge)."""
    rnd = np.random.default_rng(seed)
    rows = 24                                  # 4 m / 24 = 16.7 cm per row
    xs = (np.arange(SIZE, dtype=np.float32) + 0.5) / SIZE
    PX, PY = np.meshgrid(xs, xs)
    U = PX * rows                               # row coordinate
    row = np.floor(U).astype(int)
    fu = U - row                                # 0..1 across the row
    # stones in each row: random lengths 0.18..0.32 m summing to exactly the tile
    bounds = []
    for r_ in range(rows):
        ls = []
        while sum(ls) < TILE_M:
            ls.append(rnd.uniform(0.17, 0.32))
        ls = np.array(ls) * TILE_M / sum(ls)
        b = np.concatenate([[0], np.cumsum(ls)]) / TILE_M
        b = (b + rnd.random()) % 1.0
        bounds.append(np.sort(b[:-1]))
    H = np.zeros((SIZE, SIZE), np.float32)
    ALB = np.zeros((SIZE, SIZE, 3), np.float32)
    nst = rows * 40
    cols, fam = stone_palette(rnd, nst, mix=(0.62, 0.12, 0.22, 0.04))
    hoff = rnd.uniform(-0.1, 0.06, nst)
    tilt = rnd.normal(0, 0.5, (nst, 2))
    grain = fbm(SIZE, 256, 2, seed + 1)
    grain2 = fbm(SIZE, 128, 3, seed + 2)
    pit = fbm(SIZE, 64, 4, seed + 3)
    gapn = fbm(SIZE, 24, 4, seed + 4)
    wob = (fbm(SIZE, 16, 3, seed + 5) - 0.5) * 0.45          # rows are not ruler-straight
    fu = fu + wob * 0.5
    for r_ in range(rows):
        m = row == r_
        b = bounds[r_]
        v = PY[m]
        k = np.searchsorted(b, v, side="right") - 1          # -1 -> wraps to the last stone
        lo = np.where(k >= 0, b[k % len(b)], b[-1] - 1.0)
        hi_i = (k + 1)
        hi = np.where(hi_i < len(b), b[np.minimum(hi_i, len(b) - 1)], b[0] + 1.0)
        k = k % len(b)
        sid = r_ * 40 + k
        ev = np.minimum(v - lo, hi - v) * TILE_M                 # metres to the end joints
        eu = np.minimum(fu[m], 1 - fu[m]) * TILE_M / rows         # metres to the row joints
        e = np.minimum(eu, ev)
        gw = 0.005 + 0.006 * gapn[m]
        t = np.clip((e - gw) / 0.03, 0, 1)
        shoulder = np.sqrt(1 - (1 - t) ** 2)
        lu = (fu[m] - 0.5) * TILE_M / rows
        lv = (v - (lo + hi) / 2) * TILE_M
        h = 0.78 * shoulder + 0.1 * shoulder * np.clip(1 - (lu / 0.1) ** 2 - (lv / 0.18) ** 2, 0, 1) + hoff[sid] * shoulder
        h += (tilt[sid, 0] * lu + tilt[sid, 1] * lv) * shoulder
        h += ((pit[m] - 0.5) * 0.1 + (grain2[m] - 0.5) * 0.04) * shoulder
        h = np.where(e < gw, 0.0, h)
        H[m] = h
        base = cols[sid]
        g = grain[m][..., None]
        c = base * (1 + (g - 0.5) * 0.4) + (grain2[m][..., None] - 0.5) * 0.1
        lum = c.mean(-1, keepdims=True)
        c = lum + (c - lum) * 0.6
        c *= (0.6 + 0.4 * shoulder[..., None])
        ALB[m] = c
    H = np.clip(H, 0, 1.0)
    soil = fbm(SIZE, 16, 5, seed + 9)[..., None]
    joint = np.array([0.3, 0.26, 0.21]) * (0.7 + 0.5 * soil)
    jm = smoothstep(0.02, 0.14, H)[..., None]
    ALB = joint * (1 - jm) + ALB * jm
    cav = np.clip(H - blur(H, 5), -0.3, 0.3)
    ALB *= (1 + cav * 0.8)[..., None]
    ALB *= (0.9 + 0.14 * fbm(SIZE, 4, 4, seed + 13))[..., None]
    H = np.maximum(H, 0.06 * (0.6 + 0.8 * soil[..., 0]))
    save("paving_setts", ALB, H)
    Image.fromarray(normal_xy(H, 8.0), "RGB").save(os.path.join(OUT, "paving_setts_n.png"), optimize=True)
    print("wrote paving_setts_n")


def macro(seed=31):
    s = 512
    r = fbm(s, 4, 6, seed)
    g = fbm(s, 6, 6, seed + 1)
    b = fbm(s, 3, 5, seed + 2)
    norm = lambda a: (a - a.min()) / (a.max() - a.min())
    save("paving_macro", np.stack([norm(r), norm(g), norm(b)], -1))


if __name__ == "__main__":
    import sys
    todo = sys.argv[1:] or ["macro", "cobbles", "setts"]
    for fn in todo:
        globals()[fn]()
