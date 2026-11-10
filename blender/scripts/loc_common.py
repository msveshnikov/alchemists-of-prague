"""Shared bits for the run-2 location assets (Charles Bridge, Mala Strana, Vysehrad)."""
import math
import random

import lib_geo as G
from lib_geo import MB  # noqa: F401

PI = math.pi

G.MATS.update({
    "M_Rock": ("rock_cliff", 7.0, 0.95, 0.0, {}),
    "M_Grass": ("grass", 4.0, 0.95, 0.0, {}),
    "M_Dirt": ("dirt", 3.0, 0.95, 0.0, {}),
    "M_BridgeStone": ("stone_bridge", 3.0, 0.9, 0.0, {}),
    "M_Target": ("target_face", 0.0, 0.9, 0.0, {"fit": True}),
    "M_TavernSign": ("tavern_sign", 0.0, 0.8, 0.0, {"fit": True}),
    "M_Gravestone": ("gravestone", 0.0, 0.9, 0.0, {"fit": True}),
    "M_Pine": (None, 0, 0.9, 0.0, {"color": (0.035, 0.07, 0.03)}),
    "M_FarRoof": (None, 0, 0.85, 0.0, {"color": (0.55, 0.22, 0.13)}),
    "M_FarWall": (None, 0, 0.9, 0.0, {"color": (0.72, 0.62, 0.48)}),
    "M_FarWallB": (None, 0, 0.9, 0.0, {"color": (0.8, 0.74, 0.62)}),
    "M_FarWindow": (None, 0, 0.5, 0.0, {"color": (0.1, 0.09, 0.08), "emit_color": (1.0, 0.65, 0.3), "strength": 0.0}),
    "M_Water": (None, 0, 0.08, 0.0, {"color": (0.09, 0.17, 0.19)}),
})


def grid_surface(mb, nx, ny, fn, mat, smooth=True, flip=False):
    """Grid surface: fn(u, v) -> (x, y, z), u = i/nx, v = j/ny. Winding (a, a+u, a+u+v, a+v): normal = du x dv;
    pass flip=True to reverse it. fn may return (x, y, z, material) to vary the material per vertex row."""
    pts = [[fn(i / nx, j / ny) for i in range(nx + 1)] for j in range(ny + 1)]
    idx = [[mb._v(p[:3]) for p in row] for row in pts]
    for j in range(ny):
        for i in range(nx):
            q = [idx[j][i], idx[j][i + 1], idx[j + 1][i + 1], idx[j + 1][i]]
            m = pts[j][i][3] if len(pts[j][i]) > 3 else mat
            mb._quad_idx(list(reversed(q)) if flip else q, m, "world", smooth, False)


def noise2(x, y, seed=0, octaves=4):
    """Cheap smooth value noise for terrain (pure python, deterministic)."""
    def h(ix, iy):
        r = random.Random((ix * 73856093) ^ (iy * 19349663) ^ (seed * 83492791))
        return r.random()

    def vn(x, y):
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        a, b, c, d = h(ix, iy), h(ix + 1, iy), h(ix, iy + 1), h(ix + 1, iy + 1)
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    tot, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for _ in range(octaves):
        tot += amp * vn(x * f, y * f)
        norm += amp
        amp *= 0.5
        f *= 2.0
    return tot / norm


def ground_tile(name, top_mat, size=16.0):
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    h = size / 2
    mb.box((-h, -h, -0.3), (h, h, 0.0), {"+z": top_mat, "-z": "M_StoneRough", "-x": "M_StoneRough", "+x": "M_StoneRough",
                                          "-y": "M_StoneRough", "+y": "M_StoneRough"})
    mc.box((-h, -h, -0.3), (h, h, 0.0), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    root["size"] = [size, size, 0.3]
    return root


def tree_cluster(mb, x, y, z, r, rnd, mat="M_Leaves", n=3):
    for k in range(n):
        mb.sphere((x + rnd.uniform(-r, r) * 0.6, y + rnd.uniform(-r, r) * 0.6, z + r * 0.7 + rnd.uniform(0, r * 0.4)),
                  (r * rnd.uniform(0.7, 1.0), r * rnd.uniform(0.7, 1.0), r * rnd.uniform(0.6, 0.9)), mat, segs=8, rings=5,
                  noise=0.15, seed=rnd.randint(0, 9999))


def far_house(mb, x, y, z, w, d, h, rnd, yaw=0.0, wall=None, roof="M_FarRoof", windows=True):
    """Very cheap distant house: block + gable roof + a few dark windows (backdrops)."""
    with mb.at((x, y, z), rot_z=yaw):
        wm = wall or rnd.choice(["M_FarWall", "M_FarWallB", "M_Plaster_cream", "M_Plaster_ochre"])
        mb.box((-w / 2, -d / 2, -2.0), (w / 2, d / 2, h), wm)
        mb.gable_roof(-w / 2, w / 2, -d / 2, d / 2, h, h + w * 0.55, roof, under=roof, over=0.25, thick=0.2)
        mb.prism([(-w / 2, h), (w / 2, h), (0, h + w * 0.55 - 0.1)], -d / 2, -d / 2 + 0.2, wm)
        mb.prism([(-w / 2, h), (w / 2, h), (0, h + w * 0.55 - 0.1)], d / 2 - 0.2, d / 2, wm)
        if windows:
            fl = max(1, int(h / 3.2))
            nw = max(1, int(w / 2.4))
            for f in range(fl):
                for i in range(nw):
                    xc = -w / 2 + (i + 0.5) * w / nw
                    zc = 1.2 + f * 3.2
                    mb.box((xc - 0.35, -d / 2 - 0.03, zc), (xc + 0.35, -d / 2, zc + 1.2), "M_FarWindow")
