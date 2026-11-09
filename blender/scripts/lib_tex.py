"""Procedural 'hand-painted' texture generator for Alchemists of Prague.

Runs inside Blender (uses bpy only to write PNGs). All textures are generated with numpy,
tileable (unless noted), in a Gothic 1-2 inspired palette: warm stone beige, terracotta,
dark timber, muted greens, deep reds. Shading (AO in crevices) is baked into albedo the way
early-2000s RPG textures were painted.

Usage: blender -b --factory-startup -P make_textures.py
"""
import math
import os

import numpy as np

try:
    import bpy
except ImportError:  # allow import outside Blender for linting
    bpy = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "textures")


# ----------------------------------------------------------------------------- helpers
def rng(seed):
    return np.random.default_rng(seed)


def hexc(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def colorize(t, stops):
    """Map scalar field t in [0,1] through a list of hex colour stops."""
    cols = np.stack([hexc(c) for c in stops])
    t = np.clip(t, 0, 1) * (len(stops) - 1)
    i = np.clip(np.floor(t).astype(int), 0, len(stops) - 2)
    f = (t - i)[..., None]
    return cols[i] * (1 - f) + cols[i + 1] * f


def _axis(size, cells):
    u = np.arange(size) * cells / size
    i0 = np.floor(u).astype(int)
    f = u - i0
    f = f * f * (3 - 2 * f)
    return i0 % cells, (i0 + 1) % cells, f


def value_noise(size, cells, seed, cells_y=None):
    cy = cells_y or cells
    g = rng(seed).random((cy, cells))
    x0, x1, fx = _axis(size, cells)
    y0, y1, fy = _axis(size, cy)
    a = g[y0][:, x0]
    b = g[y0][:, x1]
    c = g[y1][:, x0]
    d = g[y1][:, x1]
    fx = fx[None, :]
    fy = fy[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(size, cells, octaves, seed, persistence=0.5, cells_y=None):
    tot = np.zeros((size, size))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = cells * 2 ** o
        cy = (cells_y or cells) * 2 ** o
        if c > size or cy > size:
            break
        tot += amp * value_noise(size, c, seed + o * 101, cy)
        norm += amp
        amp *= persistence
    return tot / norm


def voronoi(size, n, seed, jitter=0.85, stretch=(1.0, 1.0)):
    r = rng(seed)
    pts = r.random((n, n, 2)) * jitter + (1 - jitter) / 2
    ids = r.random((n, n))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) * (n / size)
    ci = np.floor(xs).astype(int)
    cj = np.floor(ys).astype(int)
    f1 = np.full((size, size), 9.0, np.float32)
    f2 = np.full((size, size), 9.0, np.float32)
    idv = np.zeros((size, size), np.float32)
    sx, sy = stretch
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            nx = ci + di
            ny = cj + dj
            p = pts[ny % n, nx % n]
            px = nx + p[..., 0]
            py = ny + p[..., 1]
            d = np.sqrt(((xs - px) * sx) ** 2 + ((ys - py) * sy) ** 2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            idv = np.where(closer, ids[ny % n, nx % n], idv)
            f1 = np.where(closer, d, f1)
    return f1, f2, idv


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def save(name, rgb, alpha=None):
    os.makedirs(OUT, exist_ok=True)
    h, w = rgb.shape[:2]
    a = np.ones((h, w)) if alpha is None else alpha
    rgba = np.dstack([np.clip(rgb, 0, 1), np.clip(a, 0, 1)])[::-1].astype(np.float32)
    path = os.path.join(OUT, name + ".png")
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("  texture", name, f"{w}x{h}")
    return path


def save_pair(name, albedo, height, strength):
    save(name, albedo)
    save(name + "_n", normal_from_height(height, strength))


def grime(size, seed, amount=0.25, cells=3):
    """Large soft dirt variation used to break up tiling. Returns multiplier ~[1-amount,1]."""
    g = fbm(size, cells, 6, seed, 0.55)
    return 1.0 - amount * smoothstep(0.35, 0.8, g)


# ----------------------------------------------------------------------------- stone
def tex_cobble(size=1024, seed=11):
    f1, f2, idv = voronoi(size, 12, seed, 0.8)
    edge = f2 - f1
    mask = smoothstep(0.03, 0.15, edge)
    dome = np.clip(1 - f1 / 0.62, 0, 1) ** 0.6
    fine = fbm(size, 32, 4, seed + 1)
    h = mask * (0.55 + 0.45 * dome) + (fine - 0.5) * 0.08
    stone = colorize(idv, ["#5f564b", "#7a6c5a", "#8e7e68", "#6d6457", "#9a8a72", "#6a5d4d"])
    stone *= (0.82 + 0.3 * fbm(size, 16, 4, seed + 2))[..., None]
    gap = colorize(fbm(size, 8, 4, seed + 3), ["#2b241d", "#3a3127"])
    shade = (0.7 + 0.42 * dome)[..., None]
    alb = lerp(gap, stone * shade, mask[..., None])
    alb *= grime(size, seed + 4, 0.22)[..., None]
    save_pair("cobble", alb, h, 6.0)


def _blocks(size, rows, seed, wmin=0.6, wmax=1.4, cols_per_row=5):
    """Ashlar block layout. Returns (dist_to_edge_px, block_id, local_v)."""
    r = rng(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    rowh = 1.0 / rows
    row = np.minimum((ys / rowh).astype(int), rows - 1)
    dist = np.zeros((size, size), np.float32)
    bid = np.zeros((size, size), np.float32)
    for ri in range(rows):
        widths = r.uniform(wmin, wmax, cols_per_row)
        b = np.concatenate([[0], np.cumsum(widths)]) / widths.sum()
        b = (b + r.random()) % 1.0
        b = np.sort(np.concatenate([b, b - 1, b + 1]))
        sel = row == ri
        x = xs[sel]
        k = np.searchsorted(b, x, side="right")
        left = b[k - 1]
        right = b[k]
        dx = np.minimum(x - left, right - x) * size
        y = ys[sel] - ri * rowh
        dy = np.minimum(y, rowh - y) * size
        dist[sel] = np.minimum(dx, dy)
        bid[sel] = ((k * 0.6180339 + ri * 0.3819) % 1.0)
    return dist, bid


def tex_ashlar(name, stops, mortar, size=1024, rows=8, seed=21, soot=0.0):
    dist, bid = _blocks(size, rows, seed)
    chips = fbm(size, 24, 4, seed + 5)
    bevel = smoothstep(1.5, 9 + chips * 6, dist)
    face = fbm(size, 12, 5, seed + 6)
    h = bevel * (0.75 + 0.25 * face)
    stone = colorize(np.clip(bid * 0.8 + face * 0.4 - 0.2, 0, 1), stops)
    stone *= (0.86 + 0.24 * fbm(size, 40, 3, seed + 7))[..., None]
    stone *= (0.78 + 0.22 * bevel)[..., None]
    mort = hexc(mortar)[None, None, :] * (0.8 + 0.3 * chips[..., None])
    alb = lerp(mort, stone, smoothstep(0.0, 0.25, bevel)[..., None])
    alb *= grime(size, seed + 8, 0.25 + soot)[..., None]
    if soot:
        streak = value_noise(size, 48, seed + 9, 2)
        alb *= (1 - soot * smoothstep(0.55, 0.95, streak))[..., None]
    save_pair(name, alb, h, 4.0)


def tex_smooth_stone(name, stops, size=512, seed=31):
    f = fbm(size, 6, 6, seed)
    alb = colorize(f, stops) * (0.9 + 0.15 * fbm(size, 48, 3, seed + 1))[..., None]
    alb *= grime(size, seed + 2, 0.15)[..., None]
    save_pair(name, alb, f, 1.5)


# ----------------------------------------------------------------------------- plaster
PLASTERS = {
    "plaster_ochre": "#c69c55",
    "plaster_green": "#8d977b",
    "plaster_red": "#94473a",
    "plaster_cream": "#d6c6a0",
    "plaster_beige": "#bea47e",
    "plaster_rose": "#b98472",
}


def tex_plaster(name, base, size=1024, seed=41):
    c = hexc(base)
    mott = fbm(size, 4, 6, seed, 0.55)
    streak = value_noise(size, 24, seed + 1, 2)
    speck = fbm(size, 128, 2, seed + 2)
    crack_f1, crack_f2, _ = voronoi(size, 7, seed + 3, 0.95)
    crack = 1 - smoothstep(0.0, 0.012, crack_f2 - crack_f1)
    crack *= smoothstep(0.62, 0.8, fbm(size, 6, 3, seed + 4))
    v = 0.86 + 0.22 * mott - 0.04 * smoothstep(0.55, 0.95, streak) - 0.05 * speck
    alb = c[None, None, :] * v[..., None]
    alb = lerp(alb, alb * 0.55, crack[..., None])
    # patches of exposed stone underneath (classic Gothic texture detail)
    patch = smoothstep(0.7, 0.76, fbm(size, 2, 6, seed + 5)) * 0.6
    under = colorize(fbm(size, 24, 3, seed + 6), ["#6e6050", "#8b7a62"])
    alb = lerp(alb, under, patch[..., None] * 0.85)
    alb *= grime(size, seed + 7, 0.18)[..., None]
    h = mott * 0.3 - crack * 0.5 - patch * 0.3 + speck * 0.1
    save_pair(name, alb, h, 2.0)


# ----------------------------------------------------------------------------- roofs
def tex_tiles(name, stops, size=1024, rows=10, cols=12, seed=51, scallop=0.32, moss="#5a5a36"):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    v = ys * rows
    r = np.floor(v).astype(int)
    lv = v - r
    off = 0.5 * (r % 2)
    cu = xs * cols + off
    c = np.floor(cu).astype(int)
    lu = cu - c
    bottom = 1 - scallop * (1 - np.sqrt(np.clip(1 - (2 * lu - 1) ** 2, 0, 1)))
    below = lv > bottom
    # pixels below the rounded edge belong to the tile of the next row (under it)
    r2 = np.where(below, r + 1, r)
    off2 = 0.5 * (r2 % 2)
    cu2 = xs * cols + off2
    c2 = np.floor(cu2).astype(int)
    lu2 = cu2 - c2
    tid = ((c2 % cols) * 0.7548 + (r2 % rows) * 0.5698) % 1.0
    shade = np.where(below, 0.5 + 0.1 * (lv - bottom), 0.68 + 0.42 * lv)
    edge_line = 1 - 0.5 * (1 - smoothstep(0.0, 0.025, np.abs(lv - bottom)))
    gap = smoothstep(0.0, 0.05, np.minimum(lu2, 1 - lu2))
    roundness = np.sqrt(np.clip(1 - (2 * lu2 - 1) ** 2, 0, 1))
    shade = shade * (0.8 + 0.2 * roundness) * edge_line * (0.6 + 0.4 * gap)
    base = colorize(np.clip(tid + 0.25 * fbm(size, 16, 3, seed) - 0.12, 0, 1), stops)
    base *= (0.88 + 0.2 * fbm(size, 64, 3, seed + 1))[..., None]
    alb = base * shade[..., None]
    m = smoothstep(0.6, 0.85, fbm(size, 5, 5, seed + 2)) * 0.6
    alb = lerp(alb, hexc(moss)[None, None, :] * shade[..., None], m[..., None])
    alb *= grime(size, seed + 3, 0.2)[..., None]
    h = np.where(below, 0.0, lv) * (0.6 + 0.4 * roundness) * gap
    save_pair(name, alb, h, 5.0)


# ----------------------------------------------------------------------------- wood
def tex_planks(name, stops, gapc, size=1024, planks=6, seed=61, gaps=True, nails=False):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    p = xs * planks
    pid = np.floor(p).astype(int)
    lp = p - pid
    grain = value_noise(size, 96, seed, 3) * 0.6 + value_noise(size, 40, seed + 1, 2) * 0.4
    rings = 0.5 + 0.5 * np.sin((grain * 18 + xs * 40) * math.pi)
    plank_t = (pid * 0.618) % 1.0
    t = np.clip(plank_t * 0.55 + grain * 0.5 + rings * 0.12 - 0.1, 0, 1)
    alb = colorize(t, stops)
    # knots
    r = rng(seed + 2)
    for _ in range(6):
        kx, ky = r.random(2)
        d = np.sqrt(((xs - kx + 0.5) % 1 - 0.5) ** 2 * 9 + ((ys - ky + 0.5) % 1 - 0.5) ** 2)
        alb *= (1 - 0.5 * (1 - smoothstep(0.0, 0.03, d)))[..., None]
    h = grain * 0.2
    if gaps:
        g = smoothstep(0.0, 0.035, np.minimum(lp, 1 - lp))
        alb = lerp(hexc(gapc)[None, None, :], alb * (0.8 + 0.2 * g[..., None]), g[..., None])
        # plank end seams
        seam_y = (pid * 0.371 + 0.2) % 1.0
        sd = np.abs(ys - seam_y)
        seam = 1 - (1 - smoothstep(0.0, 0.006, sd))
        alb *= (0.4 + 0.6 * seam)[..., None]
        h = h + g * 0.8
    if nails:
        for k in range(planks):
            for yy in (0.1, 0.9):
                cx = (k + 0.5) / planks
                d = np.sqrt((xs - cx) ** 2 + (ys - yy) ** 2)
                nm = 1 - smoothstep(0.004, 0.008, d)
                alb = lerp(alb, np.array([0.12, 0.11, 0.1]), nm[..., None])
    alb *= grime(size, seed + 3, 0.2)[..., None]
    save_pair(name, alb, h, 3.0)


# ----------------------------------------------------------------------------- cloth
def tex_cloth(name, stops, size=512, seed=71, weave=True, stripes=None):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    folds = fbm(size, 3, 5, seed, 0.5, cells_y=2)
    t = np.clip(0.5 + (folds - 0.5) * 1.2, 0, 1)
    alb = colorize(t, stops)
    if stripes:
        s = (np.floor(xs * stripes[0]) % 2)[..., None]
        alb = lerp(alb, alb * hexc(stripes[1]) / hexc(stops[len(stops) // 2]), s * 0.9)
    if weave:
        w = 0.5 + 0.25 * np.sin(xs * size * 1.6) + 0.25 * np.sin(ys * size * 1.6)
        alb *= (0.92 + 0.1 * w)[..., None]
    stains = smoothstep(0.62, 0.8, fbm(size, 6, 5, seed + 1))
    alb = lerp(alb, alb * 0.68, stains[..., None])
    alb *= grime(size, seed + 2, 0.15)[..., None]
    save_pair(name, alb, folds * 0.6, 2.0)


# ----------------------------------------------------------------------------- metal etc
def tex_metal(name, stops, rust, size=512, seed=81, rust_amt=0.6):
    f = fbm(size, 8, 6, seed)
    alb = colorize(f, stops)
    scratches = value_noise(size, 200, seed + 1, 6)
    alb *= (0.9 + 0.15 * scratches)[..., None]
    r = smoothstep(0.55, 0.85, fbm(size, 6, 6, seed + 2)) * rust_amt
    alb = lerp(alb, colorize(fbm(size, 30, 3, seed + 3), rust), r[..., None])
    save_pair(name, alb, f * 0.5 + r * 0.4, 2.0)


def tex_bark(size=512, seed=91):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    ridges = value_noise(size, 24, seed, 2)
    f = fbm(size, 16, 4, seed + 1, 0.5, cells_y=4)
    t = np.clip(ridges * 0.6 + f * 0.5, 0, 1)
    alb = colorize(t, ["#2f261d", "#4a3d2f", "#5f5242", "#6b5f4f"])
    save_pair("bark", alb, t, 5.0)


def tex_leaves(size=512, seed=101):
    f1, f2, idv = voronoi(size, 18, seed, 0.9)
    leaf = smoothstep(0.0, 0.12, f2 - f1) * np.clip(1 - f1 / 0.7, 0, 1)
    base = colorize(np.clip(idv * 0.7 + fbm(size, 4, 4, seed + 1) * 0.5 - 0.1, 0, 1),
                    ["#2a3a1c", "#3d5226", "#56692f", "#6e7c38", "#7f8a42"])
    alb = lerp(np.array([0.07, 0.09, 0.04]), base * (0.7 + 0.4 * leaf[..., None]), smoothstep(0, 0.3, leaf)[..., None])
    save_pair("leaves", alb, leaf, 4.0)


def tex_food(name, stops, size=256, seed=111, spots=None):
    f = fbm(size, 4, 5, seed)
    alb = colorize(f, stops)
    if spots:
        s = smoothstep(0.65, 0.8, fbm(size, 16, 3, seed + 1))
        alb = lerp(alb, hexc(spots), s[..., None])
    save_pair(name, alb, f, 2.0)


def tex_coals(size=256, seed=121):
    f1, f2, idv = voronoi(size, 10, seed, 0.9)
    crack = 1 - smoothstep(0.0, 0.07, f2 - f1)
    lump = colorize(idv * 0.5 + fbm(size, 8, 3, seed) * 0.5, ["#141110", "#2a2420", "#3a302a"])
    glow = colorize(fbm(size, 4, 3, seed + 1), ["#ff5a14", "#ffa040", "#ffd27a"])
    alb = lerp(lump, glow * 0.6, crack[..., None])
    save("coals", alb)
    em = glow * (crack[..., None] * 1.0 + 0.15 * smoothstep(0.4, 0.8, fbm(size, 6, 3, seed + 2))[..., None])
    save("coals_emit", em)


def tex_fire(size=256, seed=131):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    n = fbm(size, 4, 5, seed, 0.55, cells_y=2)
    t = np.clip((1 - ys) * 0.9 + (n - 0.5) * 0.6, 0, 1)
    alb = colorize(t, ["#ffe6a0", "#ffb040", "#ff6a10", "#c22c08", "#5a1004"])
    save("fire", alb)


# ----------------------------------------------------------------------------- glass
def tex_window(size=512, seed=141):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    n = 8
    a = (xs + ys) * n
    b = (xs - ys) * n
    la = np.abs(a - np.round(a))
    lb = np.abs(b - np.round(b))
    lead = 1 - smoothstep(0.03, 0.06, np.minimum(la, lb))
    pane = (np.floor(a) * 0.37 + np.floor(b) * 0.61) % 1.0
    dark = colorize(np.clip(pane * 0.6 + fbm(size, 6, 3, seed) * 0.5, 0, 1),
                    ["#1e2526", "#2b3436", "#39443f", "#4a5048"])
    sheen = smoothstep(0.55, 0.9, fbm(size, 3, 3, seed + 1))
    dark = dark + sheen[..., None] * 0.08
    leadc = np.array([0.09, 0.085, 0.08])
    save("window_glass", lerp(dark, leadc, lead[..., None]))
    lit = colorize(np.clip(pane * 0.5 + fbm(size, 5, 4, seed + 2) * 0.6 - 0.05, 0, 1),
                   ["#c25a18", "#e88a2c", "#ffb04a", "#ffcf7a"])
    save("window_lit", lerp(lit, leadc * 0.4, lead[..., None]))


def tex_lantern_glass(size=256, seed=151):
    n = fbm(size, 4, 4, seed)
    save("lantern_glow", colorize(n, ["#ff9a30", "#ffc060", "#ffe0a0"]))


# ----------------------------------------------------------------------------- decals (non-tiling)
def _circle(xs, ys, cx, cy, r):
    return np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) < r


def _seg_dist(xs, ys, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((xs - ax) * vx + (ys - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
    return np.sqrt((xs - ax - t * vx) ** 2 + (ys - ay - t * vy) ** 2)


def _polyline(xs, ys, pts, w):
    m = np.zeros(xs.shape, bool)
    for a, b in zip(pts[:-1], pts[1:]):
        m |= _seg_dist(xs, ys, a, b) < w
    return m


def _ellipse(xs, ys, cx, cy, rx, ry, ang=0.0):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = xs - cx, ys - cy
    u = (dx * c + dy * s) / rx
    v = (-dx * s + dy * c) / ry
    return u * u + v * v < 1


def lion_mask(xs, ys):
    """Rampant heraldic lion with double tail, facing viewer's left. Coords in [0,1], y down."""
    m = _ellipse(xs, ys, 0.52, 0.50, 0.11, 0.21, -0.35)          # torso
    m |= _ellipse(xs, ys, 0.45, 0.30, 0.13, 0.11, 0.2)           # mane
    m |= _ellipse(xs, ys, 0.36, 0.27, 0.08, 0.06, -0.2)          # muzzle
    m |= _polyline(xs, ys, [(0.30, 0.31), (0.27, 0.34)], 0.018)  # jaw/tongue
    m |= _polyline(xs, ys, [(0.44, 0.40), (0.33, 0.36), (0.24, 0.30)], 0.035)  # fore leg up
    m |= _polyline(xs, ys, [(0.24, 0.30), (0.20, 0.26)], 0.02)
    m |= _polyline(xs, ys, [(0.46, 0.48), (0.35, 0.50), (0.27, 0.46)], 0.032)  # fore leg 2
    m |= _polyline(xs, ys, [(0.27, 0.46), (0.22, 0.44)], 0.018)
    m |= _polyline(xs, ys, [(0.55, 0.66), (0.47, 0.76), (0.42, 0.88)], 0.045)  # hind leg
    m |= _polyline(xs, ys, [(0.42, 0.88), (0.34, 0.90)], 0.025)
    m |= _polyline(xs, ys, [(0.60, 0.64), (0.66, 0.76), (0.62, 0.90)], 0.04)  # hind leg 2
    m |= _polyline(xs, ys, [(0.62, 0.90), (0.70, 0.92)], 0.022)
    tail = [(0.63, 0.66), (0.74, 0.60), (0.80, 0.48), (0.78, 0.36), (0.72, 0.28)]
    m |= _polyline(xs, ys, tail, 0.018)
    m |= _polyline(xs, ys, [(0.80, 0.48), (0.86, 0.40), (0.86, 0.30), (0.82, 0.24)], 0.016)
    m |= _circle(xs, ys, 0.72, 0.26, 0.03) | _circle(xs, ys, 0.82, 0.22, 0.028)
    return m


def crown_mask(xs, ys):
    m = (ys > 0.15) & (ys < 0.19) & (xs > 0.37) & (xs < 0.53)
    for cx in (0.38, 0.45, 0.52):
        m |= _polyline(xs, ys, [(cx, 0.17), (cx, 0.11)], 0.012) & (ys < 0.19)
    return m


def tex_banner(size=1024, seed=161):
    h, w = size, size // 2
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ys /= h
    xs /= w
    folds = 0.5 + 0.5 * np.sin(xs * math.pi * 5 + fbm(h, 3, 3, seed)[:, :w] * 2)
    red = colorize(fbm(h, 4, 5, seed + 1)[:, :w], ["#5c1612", "#7a1f19", "#8f2a20"])
    red *= (0.8 + 0.25 * folds)[..., None]
    # lion occupies the middle; map banner coords into lion box
    lx = (xs - 0.05) / 0.9
    ly = (ys - 0.18) / 0.5
    lm = lion_mask(lx, ly)
    cm = crown_mask(lx, ly)
    white = colorize(fbm(h, 8, 3, seed + 2)[:, :w], ["#cfc3a8", "#e6dcc6"])
    gold = colorize(fbm(h, 8, 3, seed + 3)[:, :w], ["#9a7428", "#d2a84a"])
    alb = np.where(lm[..., None], white * (0.85 + 0.2 * folds[..., None]), red)
    alb = np.where(cm[..., None], gold, alb)
    border = (ys < 0.03) | (np.abs(xs - 0.5) > 0.47)
    alb = np.where(border[..., None], gold * 0.8, alb)
    alb *= grime(h, seed + 4, 0.15)[:, :w][..., None]
    save("banner_lion", alb)


def tex_shield(size=512, seed=171):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    red = colorize(fbm(size, 4, 5, seed), ["#5a1611", "#7c2018", "#8e2b20"])
    planks = 0.85 + 0.15 * (np.floor(xs * 5) % 2)
    red *= planks[..., None]
    lm = lion_mask((xs - 0.1) / 0.8, (ys - 0.08) / 0.84)
    cm = crown_mask((xs - 0.1) / 0.8, (ys - 0.08) / 0.84)
    white = colorize(fbm(size, 8, 3, seed + 1), ["#c9bda0", "#e2d8c0"])
    gold = colorize(fbm(size, 8, 3, seed + 3), ["#9a7428", "#d2a84a"])
    alb = np.where(lm[..., None], white, red)
    alb = np.where(cm[..., None], gold, alb)
    alb *= grime(size, seed + 2, 0.3)[..., None]
    save("shield_lion", alb)


def tex_astro_dial(size=1024, seed=181):
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2
    ys = -ys  # y up
    r = np.sqrt(xs ** 2 + ys ** 2)
    ang = np.arctan2(ys, xs)
    gold = colorize(fbm(size, 16, 3, seed), ["#8a6420", "#c99a3c", "#e8c060"])
    stone = colorize(fbm(size, 8, 4, seed + 1), ["#6e6150", "#8a7a64"])
    # sky zones: blue day upper, dawn/dusk orange band, black night bottom
    blue = colorize(fbm(size, 6, 3, seed + 2), ["#1f4e7a", "#2f6a9a"])
    orange = colorize(fbm(size, 6, 3, seed + 3), ["#a0451c", "#c8642a"])
    black = np.array([0.08, 0.07, 0.07])
    zone = np.where(ys > -0.15, 0, np.where(ys > -0.55, 1, 2))
    inner = np.where((zone == 0)[..., None], blue, np.where((zone == 1)[..., None], orange, black))
    alb = np.where((r < 0.8)[..., None], inner, stone)
    # outer ring dark with gold hour ticks
    ring = (r >= 0.8) & (r < 0.98)
    alb = np.where(ring[..., None], np.array([0.1, 0.09, 0.08]), alb)
    tick = (np.abs(((ang / (2 * math.pi) * 24) % 1) - 0.5) > 0.42) & (r > 0.83) & (r < 0.95)
    alb = np.where(tick[..., None], gold, alb)
    for rr in (0.8, 0.98):
        alb = np.where((np.abs(r - rr) < 0.012)[..., None], gold, alb)
    # zodiac ring (eccentric)
    zr = np.sqrt(xs ** 2 + (ys - 0.22) ** 2)
    zring = (zr > 0.46) & (zr < 0.56)
    alb = np.where(zring[..., None], gold * 0.9, alb)
    za = np.arctan2(ys - 0.22, xs)
    zt = zring & (np.abs(((za / (2 * math.pi) * 12) % 1) - 0.5) > 0.46)
    alb = np.where(zt[..., None], np.array([0.15, 0.1, 0.05]), alb)
    # earth centre + hand with sun
    alb = np.where((r < 0.12)[..., None], colorize(fbm(size, 8, 2, seed + 4), ["#2a4a2a", "#4a6a3a"]), alb)
    hand = _seg_dist(xs, ys, (0, 0), (0.55, 0.5)) < 0.018
    alb = np.where(hand[..., None], gold, alb)
    alb = np.where(_circle(xs, ys, 0.36, 0.33, 0.07)[..., None], np.array([0.98, 0.78, 0.3]), alb)
    alb = np.where((np.abs(r - 0.12) < 0.01)[..., None], gold, alb)
    save("dial_astro", alb)


def tex_calendar_dial(size=1024, seed=191):
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2
    ys = -ys
    r = np.sqrt(xs ** 2 + ys ** 2)
    ang = np.arctan2(ys, xs)
    gold = colorize(fbm(size, 16, 3, seed), ["#8a6420", "#c99a3c", "#e8c060"])
    stone = colorize(fbm(size, 8, 4, seed + 1), ["#6e6150", "#8a7a64"])
    seg = np.floor((ang / (2 * math.pi) + 0.5) * 12).astype(int)
    medal_cols = np.stack([hexc(c) for c in ["#7a2a20", "#2a4a6a", "#4a6a3a", "#8a6a2a"] * 3])
    alb = np.where((r < 0.97)[..., None], gold * 0.9, stone)
    band = (r > 0.55) & (r < 0.9)
    alb = np.where(band[..., None], medal_cols[seg % 12] * (0.8 + 0.3 * fbm(size, 10, 3, seed + 2)[..., None]), alb)
    div = band & (np.abs(((ang / (2 * math.pi) * 12) % 1) - 0.5) > 0.47)
    alb = np.where(div[..., None], gold, alb)
    inner = r < 0.35
    alb = np.where(inner[..., None], colorize(fbm(size, 4, 3, seed + 3), ["#5c1612", "#7a1f19"]), alb)
    lm = lion_mask((xs + 0.35) / 0.7, (-ys + 0.35) / 0.7) & inner
    alb = np.where(lm[..., None], np.array([0.85, 0.8, 0.7]), alb)
    for rr in (0.35, 0.55, 0.9, 0.97):
        alb = np.where((np.abs(r - rr) < 0.012)[..., None], gold, alb)
    save("dial_calendar", alb)


def tex_clock_simple(size=512, seed=201):
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2
    ys = -ys
    r = np.sqrt(xs ** 2 + ys ** 2)
    ang = np.arctan2(ys, xs)
    face = colorize(fbm(size, 6, 3, seed), ["#d8ccb0", "#ece2c8"])
    stone = colorize(fbm(size, 8, 4, seed + 1), ["#6e6150", "#8a7a64"])
    alb = np.where((r < 0.95)[..., None], face, stone)
    tick = (np.abs(((ang / (2 * math.pi) * 12) % 1) - 0.5) > 0.44) & (r > 0.72) & (r < 0.88)
    alb = np.where(tick[..., None], np.array([0.12, 0.1, 0.08]), alb)
    alb = np.where((np.abs(r - 0.95) < 0.03)[..., None], np.array([0.15, 0.13, 0.1]), alb)
    hand = (_seg_dist(xs, ys, (0, 0), (0.0, 0.6)) < 0.03) | (_seg_dist(xs, ys, (0, 0), (0.4, -0.15)) < 0.035)
    alb = np.where(hand[..., None], np.array([0.12, 0.1, 0.08]), alb)
    save("dial_clock", alb)


def tex_flowers(size=256, seed=211):
    f1, f2, idv = voronoi(size, 10, seed, 0.9)
    petal = np.clip(1 - f1 / 0.6, 0, 1)
    cols = colorize(idv, ["#c0201c", "#e04040", "#d85a9a", "#f0d050", "#c0201c"])
    green = colorize(fbm(size, 8, 3, seed + 1), ["#2a3a1a", "#4a5a2a"])
    alb = lerp(green, cols, smoothstep(0.3, 0.55, petal)[..., None])
    save("flowers", alb)


def generate_all():
    print("Generating textures into", OUT)
    tex_cobble()
    tex_ashlar("stone_ashlar", ["#8c765a", "#9d866a", "#ab9576", "#b8a283", "#937d62"], "#5e5242", seed=21)
    tex_ashlar("stone_dark", ["#4a443d", "#57514a", "#625b52", "#6e675c", "#514b44"], "#2f2b27", seed=22, soot=0.15)
    tex_ashlar("stone_wall_rough", ["#7c6a52", "#8d7860", "#9c866c", "#715f4a"], "#463c30", rows=6, seed=23)
    tex_smooth_stone("stone_trim", ["#a08c6c", "#b49f7e", "#c2ad8c"])
    tex_smooth_stone("stone_trim_dark", ["#4f4942", "#5e574e", "#6a6258"], seed=32)
    for i, (n, c) in enumerate(PLASTERS.items()):
        tex_plaster(n, c, seed=41 + 13 * i)
    tex_tiles("roof_tiles", ["#8c3a24", "#a2472b", "#b4573a", "#c06640", "#9a4630"])
    tex_tiles("roof_slate", ["#2c2e33", "#383a40", "#43464c", "#4e5056"], rows=14, cols=16, seed=52,
              scallop=0.45, moss="#3e4234")
    tex_tiles("roof_shingle", ["#4a3a2a", "#5a4632", "#6a543c", "#3e3024"], rows=12, cols=9, seed=53,
              scallop=0.05, moss="#4a4a30")
    tex_planks("wood_dark", ["#2e2118", "#3d2c1f", "#4d3826", "#5c4430"], "#140e0a", seed=61)
    tex_planks("wood_door", ["#33241a", "#432f20", "#553c28"], "#120c08", planks=5, seed=62, nails=True)
    tex_planks("wood_light", ["#5e4a36", "#76603f", "#8a714c", "#9a8260"], "#2a2016", planks=4, seed=63)
    tex_planks("timber", ["#2a1e16", "#3a2a1e", "#4a3626"], "#1a120c", planks=3, seed=64, gaps=False)
    tex_cloth("canvas", ["#a89272", "#c4ae88", "#d6c29c", "#e0cfab"])
    tex_cloth("cloth_red", ["#4e1410", "#6c1c16", "#84281e"], seed=72)
    tex_cloth("cloth_green", ["#3a4429", "#4c5834", "#5e6a40"], seed=73)
    tex_cloth("canvas_striped", ["#b8a07a", "#d2bc94", "#e0cca6"], seed=74, stripes=(8, "#8a2a20"))
    tex_cloth("burlap", ["#7a6648", "#937c58", "#a88f68"], seed=75)
    tex_metal("iron", ["#232220", "#34322f", "#46433f"], ["#4a2a18", "#6e3e20", "#8a5028"], seed=81)
    tex_metal("brass", ["#7a5a20", "#a07a30", "#c89a48"], ["#3e5a40", "#4f7058"], seed=82, rust_amt=0.3)
    tex_metal("copper_green", ["#3e6252", "#4f7a66", "#64907a"], ["#2a3e34", "#355046"], seed=83, rust_amt=0.4)
    tex_metal("steel", ["#6a6c6e", "#86888a", "#a2a4a6"], ["#5a3a24", "#7a4a28"], seed=84, rust_amt=0.25)
    tex_bark()
    tex_leaves()
    tex_food("meat", ["#4a220e", "#7a3a16", "#a05424", "#c07034"], seed=111, spots="#3a1a0a")
    tex_food("bread", ["#7a4a1e", "#a06a32", "#c08848", "#d8a868"], seed=112, spots="#e8dcc0")
    tex_food("pottery", ["#7a3e26", "#985032", "#ae6440"], seed=113)
    tex_food("clay_pale", ["#a08a6a", "#b8a07c", "#c8b28e"], seed=114)
    tex_coals()
    tex_fire()
    tex_window()
    tex_lantern_glass()
    tex_banner()
    tex_shield()
    tex_astro_dial()
    tex_calendar_dial()
    tex_clock_simple()
    tex_flowers()
    print("Textures done")
