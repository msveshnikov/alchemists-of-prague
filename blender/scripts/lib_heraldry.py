"""Heraldic shapes as numpy masks (no Blender needed): the crowned, double-tailed Bohemian lion.

All shapes live in a unit box, x right, y DOWN (image convention). The lion is rampant and faces the
viewer's left, as on the arms of Bohemia and on Vaclav's shield / surcoat in concept/characters/vaclav.png.
lion_masks(xs, ys) -> dict of boolean masks: body (white), crown (gold), tongue / claws (gold), outline.
"""
import math

import numpy as np


# ----------------------------------------------------------------------------- primitives
def poly_mask(xs, ys, pts):
    """Even-odd point-in-polygon, vectorised over the pixel grid."""
    m = np.zeros(xs.shape, bool)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if y0 == y1:
            continue
        cond = (ys >= min(y0, y1)) & (ys < max(y0, y1))
        xc = x0 + (ys - y0) * (x1 - x0) / (y1 - y0)
        m ^= cond & (xs < xc)
    return m


def ellipse_mask(xs, ys, cx, cy, rx, ry, ang=0.0):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = xs - cx, ys - cy
    u = (dx * c + dy * s) / rx
    v = (-dx * s + dy * c) / ry
    return u * u + v * v < 1


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for k in range(n + 1):
        t = k / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def stroke_mask(xs, ys, pts, w0, w1=None):
    """Thick polyline whose half-width tapers linearly from w0 to w1 (capsule per segment)."""
    w1 = w0 if w1 is None else w1
    m = np.zeros(xs.shape, bool)
    n = len(pts) - 1
    # bounding box to keep it fast
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        wa = w0 + (w1 - w0) * i / n
        wb = w0 + (w1 - w0) * (i + 1) / n
        pad = max(wa, wb)
        sel = (xs > min(ax, bx) - pad) & (xs < max(ax, bx) + pad) & (ys > min(ay, by) - pad) & (ys < max(ay, by) + pad)
        if not sel.any():
            continue
        px, py = xs[sel], ys[sel]
        vx, vy = bx - ax, by - ay
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy + 1e-12), 0, 1)
        d = np.sqrt((px - ax - t * vx) ** 2 + (py - ay - t * vy) ** 2)
        m[sel] |= d < (wa + (wb - wa) * t)
    return m


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


# ----------------------------------------------------------------------------- the lion
def _claws(xs, ys, tip, direction, size):
    """Three curved claws fanning out of a paw."""
    m = np.zeros(xs.shape, bool)
    dx, dy = direction
    L = math.hypot(dx, dy)
    dx, dy = dx / L, dy / L
    px, py = -dy, dx
    for k in (-1, 0, 1):
        sx = tip[0] + px * k * size * 0.55
        sy = tip[1] + py * k * size * 0.55
        ex = sx + (dx + px * k * 0.35) * size
        ey = sy + (dy + py * k * 0.35) * size
        cx_ = ex + (px * 0.6 - dx * 0.2) * size * 0.5
        cy_ = ey + (py * 0.6 - dy * 0.2) * size * 0.5
        m |= stroke_mask(xs, ys, bezier((sx, sy), ((sx + ex) / 2, (sy + ey) / 2), (ex, ey), (cx_, cy_), 6), size * 0.16, size * 0.03)
    return m


def lion_masks(xs, ys):
    body = np.zeros(xs.shape, bool)
    # torso: deep chest up-left, narrow waist, haunch down-right
    body |= poly_mask(xs, ys, [(0.36, 0.30), (0.47, 0.25), (0.56, 0.33), (0.60, 0.45), (0.62, 0.55), (0.68, 0.62),
                               (0.68, 0.72), (0.60, 0.76), (0.52, 0.70), (0.48, 0.58), (0.42, 0.47), (0.36, 0.40)])
    body |= ellipse_mask(xs, ys, 0.62, 0.66, 0.085, 0.10, 0.5)      # haunch
    body |= ellipse_mask(xs, ys, 0.44, 0.34, 0.095, 0.11, -0.4)     # chest
    # head: round skull, square muzzle, open jaws; mane of flame-like locks flowing back down the neck
    body |= ellipse_mask(xs, ys, 0.385, 0.195, 0.088, 0.08, -0.25)
    for k in range(10):
        a = math.radians(-115 + k * 21)
        r0, r1 = 0.05, 0.135 + 0.02 * (k % 2)
        cx, cy = 0.43, 0.23
        p0 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
        p3 = (cx + r1 * math.cos(a + 0.35), cy + r1 * math.sin(a + 0.35))
        p1 = (cx + (r0 + r1) * 0.5 * math.cos(a - 0.1), cy + (r0 + r1) * 0.5 * math.sin(a - 0.1))
        body |= stroke_mask(xs, ys, bezier(p0, p1, p1, p3, 10), 0.04, 0.006)
    body |= poly_mask(xs, ys, [(0.33, 0.145), (0.255, 0.15), (0.245, 0.17), (0.25, 0.19), (0.30, 0.20), (0.34, 0.20)])  # muzzle
    body |= poly_mask(xs, ys, [(0.33, 0.235), (0.27, 0.245), (0.262, 0.262), (0.31, 0.27), (0.37, 0.255)])            # lower jaw
    body |= poly_mask(xs, ys, [(0.38, 0.125), (0.395, 0.08), (0.425, 0.125)])                                           # ear
    # forelegs raised (upper reaches high, lower reaches forward)
    body |= stroke_mask(xs, ys, bezier((0.43, 0.33), (0.36, 0.33), (0.27, 0.36), (0.20, 0.31), 16), 0.042, 0.022)
    body |= stroke_mask(xs, ys, bezier((0.46, 0.42), (0.40, 0.48), (0.31, 0.50), (0.24, 0.47), 16), 0.04, 0.022)
    # hind legs: one kicks forward, one stands
    body |= stroke_mask(xs, ys, bezier((0.60, 0.66), (0.50, 0.72), (0.40, 0.72), (0.33, 0.80), 18), 0.06, 0.024)
    body |= stroke_mask(xs, ys, bezier((0.66, 0.70), (0.68, 0.80), (0.62, 0.86), (0.58, 0.93), 18), 0.055, 0.024)
    body |= stroke_mask(xs, ys, [(0.58, 0.93), (0.52, 0.945)], 0.026, 0.018)                              # standing foot
    # the double tail (queue fourchée) rising in an S, each end with a flame-like tuft
    stem = bezier((0.68, 0.70), (0.80, 0.68), (0.84, 0.56), (0.80, 0.47), 18)
    body |= stroke_mask(xs, ys, stem, 0.022, 0.016)
    for (p1, p2, p3) in (((0.74, 0.40), (0.70, 0.32), (0.74, 0.24)), ((0.88, 0.42), (0.92, 0.32), (0.86, 0.24))):
        c = bezier((0.80, 0.47), p1, p2, p3, 16)
        body |= stroke_mask(xs, ys, c, 0.016, 0.011)
        ex, ey = p3
        tuft = [(ex - 0.035, ey + 0.02), (ex - 0.045, ey - 0.03), (ex - 0.01, ey - 0.015), (ex, ey - 0.07),
                (ex + 0.015, ey - 0.02), (ex + 0.045, ey - 0.04), (ex + 0.035, ey + 0.02)]
        body |= poly_mask(xs, ys, tuft)
    # gold: claws, tongue, crown
    gold = np.zeros(xs.shape, bool)
    gold |= _claws(xs, ys, (0.20, 0.31), (-0.6, -0.8), 0.05)
    gold |= _claws(xs, ys, (0.24, 0.47), (-1.0, -0.2), 0.05)
    gold |= _claws(xs, ys, (0.33, 0.80), (-0.7, 0.4), 0.05)
    gold |= _claws(xs, ys, (0.52, 0.945), (-1.0, 0.1), 0.045)
    tongue = stroke_mask(xs, ys, bezier((0.31, 0.22), (0.26, 0.215), (0.235, 0.245), (0.205, 0.235), 10), 0.013, 0.006)
    crown = poly_mask(xs, ys, [(0.335, 0.125), (0.33, 0.045), (0.355, 0.085), (0.38, 0.02), (0.405, 0.08), (0.435, 0.03),
                               (0.44, 0.12), (0.39, 0.135)])
    gold |= tongue | crown
    body &= ~gold
    # eye
    eye = ellipse_mask(xs, ys, 0.345, 0.172, 0.013, 0.008, -0.3)
    return {"body": body, "gold": gold, "crown": crown, "eye": eye}


def lion_layers(xs, ys, size_px):
    """Body / gold / dark outline masks; outline thickness scales with the image."""
    m = lion_masks(xs, ys)
    allm = m["body"] | m["gold"]
    r = max(1, int(round(size_px * 0.004)))
    outline = dilate(allm, r) & ~allm
    # interior hatching lines that suggest musculature (thin dark strokes inside the body)
    hatch = np.zeros(xs.shape, bool)
    for curve, w in ((bezier((0.47, 0.30), (0.50, 0.38), (0.52, 0.48), (0.55, 0.56), 10), 0.004),
                     (bezier((0.58, 0.60), (0.63, 0.62), (0.66, 0.66), (0.66, 0.71), 8), 0.004),
                     (bezier((0.40, 0.25), (0.43, 0.27), (0.46, 0.27), (0.49, 0.26), 8), 0.003)):
        hatch |= stroke_mask(xs, ys, curve, w)
    hatch &= m["body"]
    return {"body": m["body"], "gold": m["gold"], "outline": outline | m["eye"], "hatch": hatch}


if __name__ == "__main__":
    # quick visual check outside Blender:  python lib_heraldry.py out.png
    import sys
    from PIL import Image
    S = 512
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32) / S
    L = lion_layers(xs, ys, S)
    img = np.zeros((S, S, 3), np.float32)
    img[:] = (0.45, 0.1, 0.08)
    img[L["body"]] = (0.9, 0.87, 0.8)
    img[L["gold"]] = (0.85, 0.65, 0.25)
    img[L["hatch"]] = (0.6, 0.55, 0.5)
    img[L["outline"]] = (0.1, 0.05, 0.03)
    Image.fromarray((img * 255).astype(np.uint8)).save(sys.argv[1] if len(sys.argv) > 1 else "lion.png")
