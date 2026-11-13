"""Seal the joined Prague world so the player cannot leave the four districts for the empty fields around them.

    godot --headless --path . scenes/game.tscn -- --reach --no-seal     # renders/world/reach_open.{bin,json,png}
    python tools/seal_world.py [--preview]                               # -> assets/levels/prague_seal.json
    godot --headless --path . scenes/game.tscn -- --reach [--reach-jump] # sealed grid: renders/world/reach.*
    python tools/seal_world.py --check                                   # leaks -> renders/world/seal_check.png

How: the open reachability grid from scripts/reach_probe.gd (1 m cells the player can stand on and walk to) is split
into "town" (cells near gameplay content: doors, lanterns, stalls, townsfolk, patrol routes...) and "field" (farther
than FAR from all of it). A minimum vertex cut between the two finds the narrowest
places that separate them -- the alleys between houses and the open street ends. Every connected run of cut cells
becomes a stone wall (garden_wall stretched to fit, with an invisible collider). Ground tiles that end up wholly in the
sealed-off field are listed too; the game hides them so the land beyond the walls is meadow, not an empty square.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as nd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow, breadth_first_order

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LV = os.path.join(ROOT, "assets", "levels")
RW = os.path.join(ROOT, "renders", "world")

NEAR = 3.0          # free cells this close to content are town (flow sources)
FAR = 22.0          # free cells farther than this from all content are field (flow sinks)
SKIP_PROPS = {"tree", "pine_tree", "rock_outcrop", "boat_row", "boat_barge", "jetty", "cliff_rock_a", "cliff_rock_b",
              "flag_pole", "fence_wood", "garden_wall", "fortress_wall", "fortress_parapet", "fortress_tower",
              "retaining_wall", "embankment", "gravestone", "grave_cross"}


def load_grid():
    info = json.load(open(os.path.join(RW, "reach_open.json")))
    g = np.fromfile(os.path.join(RW, "reach_open.bin"), dtype=np.float32).reshape(info["nz"], info["nx"])
    return info, g


def content_points(layout, pop):
    pts = []
    for m in layout["markers"]:
        if m["kind"] in ("window", "interior"):
            continue
        pts.append(m["pos"])
    for i in layout["instances"]:
        a = i["asset"]
        if a.startswith(("house", "ground", "road", "bridge", "cliff")) or a in SKIP_PROPS:
            continue
        pts.append(i["pos"])
    for e in pop["population"]:
        pts.append(e["pos"])
        for p in e.get("route_points", []):
            pts.append(p)
    return pts


def min_cut(free, src, snk):
    """Vertex min cut on the 8-connected grid of free cells. Returns a bool mask of cut cells."""
    nz, nx = free.shape
    idx = -np.ones(free.shape, np.int64)
    cells = np.flatnonzero(free.ravel())
    idx.ravel()[cells] = np.arange(cells.size)
    n = cells.size
    S, T = 2 * n, 2 * n + 1
    BIG = 1 << 20
    rows, cols, caps = [], [], []
    ii = np.arange(n)
    rows.append(2 * ii); cols.append(2 * ii + 1); caps.append(np.ones(n, np.int64))      # in -> out, capacity 1
    iz, ix = np.divmod(cells, nx)
    for dz, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        jz, jx = iz + dz, ix + dx
        ok = (jz >= 0) & (jz < nz) & (jx >= 0) & (jx < nx)
        a = ii[ok]
        b = idx[jz[ok], jx[ok]]
        good = b >= 0
        a, b = a[good], b[good]
        if dz == 1 and dx != 0:   # diagonal step only if one of the two orthogonal cells is free (no corner cutting)
            c1 = free[iz[a] + dz, ix[a]]
            c2 = free[iz[a], ix[a] + dx]
            keep = c1 | c2
            a, b = a[keep], b[keep]
        rows += [2 * a + 1, 2 * b + 1]; cols += [2 * b, 2 * a]; caps += [np.full(a.size, BIG), np.full(a.size, BIG)]
    s_ids = idx[src & free]
    t_ids = idx[snk & free]
    rows += [np.full(s_ids.size, S), 2 * t_ids + 1]
    cols += [2 * s_ids, np.full(t_ids.size, T)]
    caps += [np.full(s_ids.size, BIG), np.full(t_ids.size, BIG)]
    # source cells cannot be cut: raise their in->out capacity
    rows.append(2 * s_ids); cols.append(2 * s_ids + 1); caps.append(np.full(s_ids.size, BIG))
    r = np.concatenate(rows); c = np.concatenate(cols); k = np.concatenate(caps).astype(np.int32)
    G = csr_matrix((k, (r, c)), shape=(2 * n + 2, 2 * n + 2))
    G.sum_duplicates()
    res = maximum_flow(G, S, T, method="dinic")
    print("max flow (cut cells):", res.flow_value)
    resid = G - res.flow
    resid.data[resid.data < 0] = 0
    resid.eliminate_zeros()
    reach = breadth_first_order(resid, S, directed=True, return_predecessors=False)
    seen = np.zeros(2 * n + 2, bool)
    seen[reach] = True
    cut = seen[0:2 * n:2] & ~seen[1:2 * n:2]
    town = seen[1:2 * n:2]
    mask = np.zeros(free.shape, bool)
    mask.ravel()[cells[cut]] = True
    tmask = np.zeros(free.shape, bool)
    tmask.ravel()[cells[town]] = True
    return mask, tmask


def segments(cut, grid, info):
    """Cut cells -> straight wall segments (Godot x, z)."""
    x0, z0, cs = info["x0"], info["z0"], info["cell"]
    lab, n = nd.label(cut, structure=np.ones((3, 3)))
    out = []

    def fit(pts, hs):
        c = pts.mean(0)
        if len(pts) == 1:
            d = np.array([1.0, 0.0])
        else:
            u, s, vt = np.linalg.svd(pts - c)
            d = vt[0]
        t = (pts - c) @ d
        off = np.abs((pts - c) @ np.array([-d[1], d[0]]))
        if off.max() > 1.1 and len(pts) > 3:   # bent run: split at the median
            order = np.argsort(t)
            h = len(order) // 2
            return fit(pts[order[:h]], hs[order[:h]]) + fit(pts[order[h:]], hs[order[h:]])
        a = c + d * (t.min() - 0.5 * cs)
        b = c + d * (t.max() + 0.5 * cs)
        return [(a, b, float(hs.min()))]

    for k in range(1, n + 1):
        zz, xx = np.nonzero(lab == k)
        pts = np.stack([x0 + (xx + 0.5) * cs, z0 + (zz + 0.5) * cs], 1)
        hs = grid[zz, xx]
        out += fit(pts, hs)
    return out


def extend(a, b, by):
    d = (b - a) / max(1e-6, np.linalg.norm(b - a))
    return a - d * by, b + d * by


def footprints(layout):
    """Rotated ground rectangles (Godot x, z corners) of every building, from the glTF bounds."""
    cache, out = {}, []
    for i in layout["instances"]:
        a, path = i["asset"], i["path"]
        if "/architecture/" not in path or a.startswith(("ground_", "road_")):
            continue
        if a not in cache:
            g = json.load(open(os.path.join(ROOT, path.replace("res://", "")), encoding="utf-8"))
            mn, mx = [1e9] * 3, [-1e9] * 3
            for m in g["meshes"]:
                for pr in m["primitives"]:
                    acc = g["accessors"][pr["attributes"]["POSITION"]]
                    mn = [min(u, v) for u, v in zip(mn, acc["min"])]
                    mx = [max(u, v) for u, v in zip(mx, acc["max"])]
            cache[a] = (mn, mx)
        mn, mx = cache[a]
        t = math.radians(i["yaw_deg"])
        c, s_ = math.cos(t), math.sin(t)
        pts = [(i["pos"][0] + x * c + z * s_, i["pos"][2] - x * s_ + z * c) for x in (mn[0], mx[0]) for z in (mn[2], mx[2])]
        out.append(pts)
    return out


def hidden_tiles(layout, town, info):
    """Cobble tiles wholly beyond the walls (no town cell on or next to them, no building standing on them)."""
    x0, z0, cs = info["x0"], info["z0"], info["cell"]
    fps = footprints(layout)
    out = []
    for i in layout["instances"]:
        if i["asset"] != "ground_cobble" or abs(i["pos"][1]) > 0.5:
            continue
        tx, tz = i["pos"][0], i["pos"][2]
        m = 10.0
        ix0, ix1 = int((tx - m - x0) / cs), int((tx + m - x0) / cs) + 1
        iz0, iz1 = int((tz - m - z0) / cs), int((tz + m - z0) / cs) + 1
        if town[max(0, iz0):max(0, iz1), max(0, ix0):max(0, ix1)].any():
            continue
        if any(min(p[0] for p in f) < tx + 8.5 and max(p[0] for p in f) > tx - 8.5 and
               min(p[1] for p in f) < tz + 8.5 and max(p[1] for p in f) > tz - 8.5 for f in fps):
            continue
        out.append(i["id"])
    return out


def check():
    """Compare a sealed reach grid (renders/world/reach.*) with the town found from the open one."""
    info = json.load(open(os.path.join(RW, "reach.json")))
    g = np.fromfile(os.path.join(RW, "reach.bin"), dtype=np.float32).reshape(info["nz"], info["nx"])
    town = np.load(os.path.join(RW, "seal_town.npy"))
    reach = g > -90
    leak = reach & ~nd.binary_dilation(town, iterations=2)
    lost = town & ~nd.binary_dilation(reach, iterations=2)
    print("reachable %d, town %d, leaked into the field %d, town cells lost %d" % (reach.sum(), town.sum(), leak.sum(), lost.sum()))
    from PIL import Image
    img = np.zeros(reach.shape + (3,), np.uint8)
    img[reach] = (120, 200, 120)
    img[leak] = (255, 0, 0)
    img[lost] = (0, 120, 255)
    Image.fromarray(img).resize((info["nx"] * 2, info["nz"] * 2), Image.NEAREST).save(os.path.join(RW, "seal_check.png"))
    for name, m in (("leak", leak), ("lost", lost)):
        lab, n = nd.label(m)
        for k in range(1, n + 1):
            zz, xx = np.nonzero(lab == k)
            if len(zz) >= 3:
                print("  %s %d cells around x=%.0f z=%.0f" % (name, len(zz), info["x0"] + xx.mean(), info["z0"] + zz.mean()))
    return leak.sum() == 0


def main():
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    preview = "--preview" in sys.argv
    layout = json.load(open(os.path.join(LV, "prague_layout.json"), encoding="utf-8"))
    pop = json.load(open(os.path.join(LV, "prague_population.json"), encoding="utf-8"))
    info, grid = load_grid()
    x0, z0, cs, nx, nz = info["x0"], info["z0"], info["cell"], info["nx"], info["nz"]
    free = grid > -90
    content = np.zeros(free.shape, bool)
    for p in content_points(layout, pop):
        ix, iz = int((p[0] - x0) / cs), int((p[2] - z0) / cs)
        if 0 <= ix < nx and 0 <= iz < nz:
            content[iz, ix] = True
    dist = nd.distance_transform_edt(~content) * cs
    src = free & (dist <= NEAR)
    snk = free & (dist > FAR)
    cut, town = min_cut(free, src, snk)
    segs = segments(cut, grid, info)
    walls = []
    for a, b, y in segs:
        a, b = extend(a, b, 0.6)
        walls.append({"a": [round(a[0], 2), round(a[1], 2)], "b": [round(b[0], 2), round(b[1], 2)], "y": round(y, 2)})
    print("walls:", len(walls), "total length: %.0f m" % sum(math.dist(w["a"], w["b"]) for w in walls))
    np.save(os.path.join(RW, "seal_town.npy"), town | cut)
    tiles = hidden_tiles(layout, town | cut, info)
    print("hidden cobble tiles:", len(tiles))
    data = {"note": "generated by tools/seal_world.py -- walls (Godot x, z; y = floor) closing the town off from the "
                    "empty land around it, and ground tiles beyond them that the game leaves out",
            "walls": walls, "hidden_tiles": tiles}
    # preview image: town green, field grey, cut red, content yellow
    from PIL import Image
    img = np.zeros(free.shape + (3,), np.uint8)
    img[free] = (90, 90, 90)
    img[town] = (120, 200, 120)
    img[src] = (60, 150, 60)
    img[cut] = (255, 0, 0)
    img[content] = (255, 230, 0)
    Image.fromarray(img).resize((nx * 2, nz * 2), Image.NEAREST).save(os.path.join(RW, "seal_preview.png"))
    if preview:
        json.dump(data, open(os.path.join(RW, "seal_preview.json"), "w"), indent=1)
        return
    json.dump(data, open(os.path.join(LV, "prague_seal.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
