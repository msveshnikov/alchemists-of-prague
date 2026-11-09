"""Geometry, material and export helpers shared by all asset build scripts.

Conventions (see decisions.md):
  * 1 unit = 1 m, Z up in Blender (exported as Y up glTF).
  * Building facades face Blender -Y  (= Godot +Z after import).
  * Asset root = Empty at the origin (centre of footprint, ground level).
  * Child naming:  INT_*  interactive pieces (doors, window shutters, stalls)
                   MARK_* empties marking gameplay spots (merchant, smith, spawn)
                   LIGHT_* point lights for night mode
                   *-colonly simplified collision meshes (Godot import convention)
  * UVs are world-scale planar per face, so every tileable texture keeps the same
    texel density on every asset (consistent hand-painted look).
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(SCRIPTS)
PROJECT = os.path.dirname(BLENDER_DIR)
TEX_DIR = os.path.join(BLENDER_DIR, "textures")

# ----------------------------------------------------------------------------- materials
# name: (texture, metres per texture repeat, roughness, metallic, extra)
MATS = {
    "M_Cobble": ("cobble", 2.0, 0.92, 0.0, {}),
    "M_Ashlar": ("stone_ashlar", 3.0, 0.9, 0.0, {}),
    "M_StoneDark": ("stone_dark", 3.0, 0.9, 0.0, {}),
    "M_StoneRough": ("stone_wall_rough", 3.0, 0.92, 0.0, {}),
    "M_Trim": ("stone_trim", 1.5, 0.85, 0.0, {}),
    "M_TrimDark": ("stone_trim_dark", 1.5, 0.85, 0.0, {}),
    "M_Plaster_ochre": ("plaster_ochre", 4.0, 0.95, 0.0, {}),
    "M_Plaster_green": ("plaster_green", 4.0, 0.95, 0.0, {}),
    "M_Plaster_red": ("plaster_red", 4.0, 0.95, 0.0, {}),
    "M_Plaster_cream": ("plaster_cream", 4.0, 0.95, 0.0, {}),
    "M_Plaster_beige": ("plaster_beige", 4.0, 0.95, 0.0, {}),
    "M_Plaster_rose": ("plaster_rose", 4.0, 0.95, 0.0, {}),
    "M_RoofTiles": ("roof_tiles", 2.5, 0.85, 0.0, {}),
    "M_Slate": ("roof_slate", 2.0, 0.7, 0.0, {}),
    "M_Shingle": ("roof_shingle", 2.0, 0.9, 0.0, {}),
    "M_WoodDark": ("wood_dark", 1.6, 0.85, 0.0, {}),
    "M_Door": ("wood_door", 1.4, 0.85, 0.0, {}),
    "M_WoodLight": ("wood_light", 1.2, 0.85, 0.0, {}),
    "M_Timber": ("timber", 1.5, 0.85, 0.0, {}),
    "M_Canvas": ("canvas", 2.0, 0.95, 0.0, {}),
    "M_CanvasStriped": ("canvas_striped", 2.5, 0.95, 0.0, {}),
    "M_ClothRed": ("cloth_red", 1.5, 0.95, 0.0, {}),
    "M_ClothGreen": ("cloth_green", 1.5, 0.95, 0.0, {}),
    "M_Burlap": ("burlap", 0.8, 0.98, 0.0, {}),
    "M_Iron": ("iron", 1.0, 0.6, 0.8, {}),
    "M_Steel": ("steel", 0.8, 0.35, 1.0, {}),
    "M_Brass": ("brass", 1.0, 0.4, 0.9, {}),
    "M_CopperGreen": ("copper_green", 2.0, 0.7, 0.3, {}),
    "M_Bark": ("bark", 1.2, 0.95, 0.0, {}),
    "M_Leaves": ("leaves", 1.5, 0.9, 0.0, {}),
    "M_Meat": ("meat", 0.5, 0.45, 0.0, {}),
    "M_Bread": ("bread", 0.4, 0.8, 0.0, {}),
    "M_Pottery": ("pottery", 0.6, 0.6, 0.0, {}),
    "M_ClayPale": ("clay_pale", 0.6, 0.8, 0.0, {}),
    "M_Flowers": ("flowers", 0.4, 0.9, 0.0, {}),
    "M_Coals": ("coals", 0.5, 0.9, 0.0, {"emit": "coals_emit", "strength": 3.0}),
    "M_Fire": ("fire", 0.0, 1.0, 0.0, {"emit": "fire", "strength": 6.0, "fit": True}),
    "M_WindowLit": ("window_glass", 1.2, 0.25, 0.0, {"emit": "window_lit", "strength": 1.5, "night": True}),
    "M_LanternGlass": ("lantern_glow", 0.3, 0.3, 0.0, {"emit": "lantern_glow", "strength": 5.0, "night": True}),
    "M_Banner": ("banner_lion", 0.0, 0.95, 0.0, {"fit": True}),
    "M_Shield": ("shield_lion", 0.0, 0.8, 0.0, {"fit": True}),
    "M_DialAstro": ("dial_astro", 0.0, 0.5, 0.3, {"fit": True}),
    "M_DialCalendar": ("dial_calendar", 0.0, 0.5, 0.3, {"fit": True}),
    "M_DialClock": ("dial_clock", 0.0, 0.6, 0.0, {"fit": True}),
    # flat colour materials (small props)
    "M_Apple": (None, 0, 0.5, 0.0, {"color": (0.55, 0.08, 0.05)}),
    "M_Cabbage": (None, 0, 0.7, 0.0, {"color": (0.28, 0.42, 0.16)}),
    "M_Carrot": (None, 0, 0.7, 0.0, {"color": (0.75, 0.32, 0.06)}),
    "M_Onion": (None, 0, 0.6, 0.0, {"color": (0.75, 0.6, 0.38)}),
    "M_Pumpkin": (None, 0, 0.6, 0.0, {"color": (0.72, 0.38, 0.08)}),
    "M_Candle": (None, 0, 0.6, 0.0, {"color": (0.85, 0.8, 0.65)}),
    "M_Rope": (None, 0, 0.95, 0.0, {"color": (0.45, 0.36, 0.22)}),
    "M_Leather": (None, 0, 0.7, 0.0, {"color": (0.28, 0.17, 0.09)}),
    "M_Statue": ("stone_trim", 1.0, 0.85, 0.0, {}),
    "M_Gold": ("brass", 0.5, 0.3, 1.0, {}),
}

# Materials whose emission should be off in daytime renders (night-only glow).
NIGHT_MATS = [k for k, v in MATS.items() if v[4].get("night")]


def _load_img(name, non_color=False):
    key = name + ".png"
    img = bpy.data.images.get(key)
    if img is None:
        img = bpy.data.images.load(os.path.join(TEX_DIR, key))
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    tex, _scale, rough, metal, extra = MATS[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _load_img(tex)
        t.location = (-500, 300)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        npath = os.path.join(TEX_DIR, tex + "_n.png")
        if os.path.exists(npath):
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = _load_img(tex + "_n", non_color=True)
            tn.location = (-500, -100)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-200, -100)
            nm.inputs["Strength"].default_value = 1.0
            nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        c = extra.get("color", (0.5, 0.5, 0.5))
        bsdf.inputs["Base Color"].default_value = (*c, 1.0)
    if "emit_color" in extra:
        bsdf.inputs["Emission Color"].default_value = (*extra["emit_color"], 1.0)
        bsdf.inputs["Emission Strength"].default_value = extra.get("strength", 4.0)
    if "emit" in extra:
        te = nt.nodes.new("ShaderNodeTexImage")
        te.image = _load_img(extra["emit"])
        te.location = (-500, -400)
        nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = extra["strength"]
    m["night_emission"] = bool(extra.get("night"))
    return m


def set_night_emission(on):
    """Toggle emission of night-only materials (windows, lanterns) for preview renders."""
    for name in NIGHT_MATS:
        m = bpy.data.materials.get(name)
        if not m:
            continue
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Emission Strength"].default_value = MATS[name][4]["strength"] if on else 0.0


# ----------------------------------------------------------------------------- builder
class MB:
    """Accumulates primitives (with per-face material + UV mode) into one mesh object."""

    def __init__(self):
        self.verts = []
        self.faces = []  # (idx tuple, material, uvmode, smooth, closed)
        self.stack = [Matrix.Identity(4)]

    # transform stack ------------------------------------------------------
    def push(self, m):
        self.stack.append(self.stack[-1] @ m)

    def pop(self):
        self.stack.pop()

    def at(self, loc=(0, 0, 0), rot_z=0.0, rot_x=0.0, rot_y=0.0, scale=1.0):
        m = Matrix.Translation(loc) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Rotation(rot_y, 4, "Y") \
            @ Matrix.Rotation(rot_x, 4, "X")
        if scale != 1.0:
            s = (scale, scale, scale) if not isinstance(scale, (tuple, list)) else scale
            m = m @ Matrix.Diagonal((*s, 1.0))
        return _Ctx(self, m)

    def _v(self, p):
        self.verts.append(self.stack[-1] @ Vector(p))
        return len(self.verts) - 1

    def face(self, pts, mat, uv="world", smooth=False, closed=False):
        idx = tuple(self._v(p) for p in pts)
        self.faces.append((idx, mat, uv, smooth, closed))
        return idx

    def _quad_idx(self, idx, mat, uv="world", smooth=False, closed=True):
        self.faces.append((tuple(idx), mat, uv, smooth, closed))

    # primitives -------------------------------------------------------------
    def box(self, mn, mx, mat, uv="world", skip=()):
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        v = [self._v(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        quads = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
                 "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
        for k, q in quads.items():
            if k in skip:
                continue
            m = mat[k] if isinstance(mat, dict) else mat
            self._quad_idx([v[i] for i in q], m, uv, False, True)

    def cbox(self, c, size, mat, uv="world", skip=()):
        """Box from centre + size."""
        c = Vector(c)
        s = Vector(size) / 2
        self.box(c - s, c + s, mat, uv, skip)

    def prism(self, poly, y0, y1, mat, cap=None, side_mats=None, plane="xz", uv="world", smooth=False):
        """Extrude a 2D polygon. plane 'xz': poly (x,z) extruded along y; 'xy': (x,y) along z."""
        n = len(poly)
        if plane == "xz":
            a = [self._v((p[0], y0, p[1])) for p in poly]
            b = [self._v((p[0], y1, p[1])) for p in poly]
        else:
            a = [self._v((p[0], p[1], y0)) for p in poly]
            b = [self._v((p[0], p[1], y1)) for p in poly]
        capm = cap or mat
        self._quad_idx(a, capm, uv, False, True)
        self._quad_idx(list(reversed(b)), capm, uv, False, True)
        for i in range(n):
            j = (i + 1) % n
            sm = side_mats[i] if side_mats else mat
            self._quad_idx([a[i], a[j], b[j], b[i]], sm, uv, smooth, True)

    def cyl(self, base, r, h, mat, segs=12, r_top=None, cap=True, smooth=True, cap_mat=None, uv="world"):
        """Vertical cylinder / cone / frustum standing on `base`."""
        r_top = r if r_top is None else r_top
        bx, by, bz = base
        bot = [self._v((bx + r * math.cos(2 * math.pi * i / segs), by + r * math.sin(2 * math.pi * i / segs), bz))
               for i in range(segs)]
        if r_top <= 1e-5:
            apex = self._v((bx, by, bz + h))
            for i in range(segs):
                self._quad_idx([bot[i], bot[(i + 1) % segs], apex], mat, uv, smooth, True)
        else:
            top = [self._v((bx + r_top * math.cos(2 * math.pi * i / segs),
                            by + r_top * math.sin(2 * math.pi * i / segs), bz + h)) for i in range(segs)]
            for i in range(segs):
                j = (i + 1) % segs
                self._quad_idx([bot[i], bot[j], top[j], top[i]], mat, uv, smooth, True)
            if cap:
                self._quad_idx(top, cap_mat or mat, uv, False, True)
        if cap:
            self._quad_idx(list(reversed(bot)), cap_mat or mat, uv, False, True)

    def rod(self, p0, p1, r, mat, segs=8, smooth=True, r1=None):
        """Cylinder between two points."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        q = d.normalized().to_track_quat("Z", "Y")
        m = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
        self.push(m)
        self.cyl((0, 0, 0), r, L, mat, segs, r_top=r1, smooth=smooth)
        self.pop()

    def sphere(self, c, radii, mat, segs=12, rings=8, smooth=True, noise=0.0, seed=0, z_cut=None, skip=None):
        import random
        rnd = random.Random(seed)
        cx, cy, cz = c
        rx, ry, rz = radii if isinstance(radii, (tuple, list)) else (radii,) * 3
        rows = []
        for j in range(rings + 1):
            th = math.pi * j / rings
            row = []
            for i in range(segs):
                ph = 2 * math.pi * i / segs
                k = 1.0 + (rnd.uniform(-noise, noise) if 0 < j < rings else 0)
                x = cx + rx * k * math.sin(th) * math.cos(ph)
                y = cy + ry * k * math.sin(th) * math.sin(ph)
                z = cz + rz * k * math.cos(th)
                if z_cut is not None:
                    z = max(z, z_cut)
                row.append(self._v((x, y, z)))
            rows.append(row)
        for j in range(rings):
            for i in range(segs):
                i2 = (i + 1) % segs
                if skip is not None:
                    th = math.pi * (j + 0.5) / rings
                    ph = 2 * math.pi * (i + 0.5) / segs
                    if skip(math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)):
                        continue
                self._quad_idx([rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2]], mat, "world", smooth,
                               skip is None)

    def lathe(self, profile, mat, segs=16, cap_bottom=True, cap_top=True, smooth=True, cap_mat=None, closed=True):
        """Surface of revolution around Z. profile: [(radius, z), ...] bottom to top."""
        rings = []
        for r, z in profile:
            rings.append([self._v((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z))
                          for i in range(segs)])
        for a, b in zip(rings[:-1], rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                self._quad_idx([a[i], a[j], b[j], b[i]], mat, "world", smooth, closed)
        if cap_bottom and profile[0][0] > 1e-4:
            self._quad_idx(list(reversed(rings[0])), cap_mat or mat, "world", False, closed)
        if cap_top and profile[-1][0] > 1e-4:
            self._quad_idx(rings[-1], cap_mat or mat, "world", False, closed)

    def torus(self, R, r, mat, segs=20, tsegs=8, smooth=True):
        """Torus in the local XY plane around the origin (use at(rot_x=...) to orient)."""
        rings = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ring = []
            for k in range(tsegs):
                b = 2 * math.pi * k / tsegs
                rr = R + r * math.cos(b)
                ring.append(self._v((rr * math.cos(a), rr * math.sin(a), r * math.sin(b))))
            rings.append(ring)
        for i in range(segs):
            a, b = rings[i], rings[(i + 1) % segs]
            for k in range(tsegs):
                l = (k + 1) % tsegs
                self._quad_idx([a[k], b[k], b[l], a[l]], mat, "world", smooth, True)

    def pyramid(self, cx, cy, z0, w, d, h, mat, w_top=0.0, d_top=0.0):
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
        b = [self._v(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]]
        if w_top <= 0:
            a = self._v((cx, cy, z0 + h))
            for i in range(4):
                self._quad_idx([b[i], b[(i + 1) % 4], a], mat)
        else:
            t = [self._v(p) for p in [(cx - w_top / 2, cy - d_top / 2, z0 + h), (cx + w_top / 2, cy - d_top / 2, z0 + h),
                                      (cx + w_top / 2, cy + d_top / 2, z0 + h), (cx - w_top / 2, cy + d_top / 2, z0 + h)]]
            for i in range(4):
                j = (i + 1) % 4
                self._quad_idx([b[i], b[j], t[j], t[i]], mat)
            self._quad_idx(t, mat)
        self._quad_idx(list(reversed(b)), mat)

    def gable_roof(self, x0, x1, y0, y1, z_eave, z_ridge, mat, under="M_Timber", over=0.35, thick=0.25):
        """Roof with ridge along Y. Built as an extruded thick chevron."""
        xm = (x0 + x1) / 2
        poly = [(x0 - over, z_eave - over * 0.9), (xm, z_ridge), (x1 + over, z_eave - over * 0.9),
                (x1 + over, z_eave - over * 0.9 - thick), (xm, z_ridge - thick * 1.4), (x0 - over, z_eave - over * 0.9 - thick)]
        self.prism(poly, y0, y1, mat, cap=under, side_mats=[mat, mat, under, under, under, under])

    # ------------------------------------------------------------------------ build
    def build(self, name, parent=None, collection=None):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bv = [bm.verts.new(v) for v in self.verts]
        bm.verts.ensure_lookup_table()
        mats = []
        info = []
        for idx, mat, uv, smooth, closed in self.faces:
            if len(set(idx)) < 3:
                continue
            try:
                f = bm.faces.new([bv[i] for i in idx])
            except ValueError:
                continue
            if mat not in mats:
                mats.append(mat)
            f.material_index = mats.index(mat)
            f.smooth = smooth
            info.append((f, mat, uv, closed))
        closed_faces = [f for f, _, _, c in info if c]
        # merge duplicate vertices only inside closed primitives is unnecessary; just fix normals
        bmesh.ops.recalc_face_normals(bm, faces=closed_faces)
        uvl = bm.loops.layers.uv.new("UVMap")
        for f, mat, uvmode, _ in info:
            n = f.normal
            if abs(n.z) < 0.95:
                t = Vector((0, 0, 1)).cross(n).normalized()
            else:
                t = Vector((1, 0, 0))
            b = n.cross(t).normalized()
            scale = MATS[mat][1] or 1.0
            fit = uvmode == "fit" or MATS[mat][4].get("fit")
            coords = [(l.vert.co.dot(t), l.vert.co.dot(b)) for l in f.loops]
            if fit:
                us = [c[0] for c in coords]
                vs = [c[1] for c in coords]
                du = (max(us) - min(us)) or 1
                dv = (max(vs) - min(vs)) or 1
                for l, (u, v) in zip(f.loops, coords):
                    l[uvl].uv = ((u - min(us)) / du, (v - min(vs)) / dv)
            else:
                for l, (u, v) in zip(f.loops, coords):
                    l[uvl].uv = (u / scale, v / scale)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(get_mat(m))
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        if parent:
            ob.parent = parent
        return ob


class _Ctx:
    def __init__(self, mb, m):
        self.mb, self.m = mb, m

    def __enter__(self):
        self.mb.push(self.m)
        return self.mb

    def __exit__(self, *a):
        self.mb.pop()


# ----------------------------------------------------------------------------- shapes
def arch_points(x0, x1, zs, kind="round", n=10):
    w = x1 - x0
    xm = (x0 + x1) / 2
    if kind == "flat":
        return [(x0, zs), (x1, zs)]
    if kind == "round":
        r = w / 2
        return [(xm + r * math.cos(math.pi * (1 - i / n)), zs + r * math.sin(math.pi * (1 - i / n))) for i in range(n + 1)]
    if kind == "segment":
        r = w * 0.8
        half = math.asin((w / 2) / r)
        zc = zs - r * math.cos(half)
        return [(xm + r * math.sin(-half + 2 * half * i / n), zc + r * math.cos(-half + 2 * half * i / n)) for i in range(n + 1)]
    # gothic pointed arch
    R = w * 0.8
    th_end = math.acos((w / 2 - R) / R)
    left = [(x0 + R + R * math.cos(math.pi - (math.pi - th_end) * i / (n // 2)),
             zs + R * math.sin(math.pi - (math.pi - th_end) * i / (n // 2))) for i in range(n // 2 + 1)]
    right = [(x1 - (p[0] - x0), p[1]) for p in reversed(left[:-1])]
    return left + right


def opening_outline(o):
    """Closed outline of an opening (for glass panes / door leaves)."""
    pts = [(o["xa"], o["za"])] + arch_points(o["xa"], o["xb"], o["zs"], o.get("kind", "flat")) + [(o["xb"], o["za"])]
    return pts


def wall_with_openings(mb, x0, x1, z0, z1, y0, y1, openings, mat):
    """Solid wall slab in the XZ plane with real openings (doors / windows / arches)."""
    ops = sorted(openings, key=lambda o: o["xa"])
    cur = x0
    for o in ops:
        if o["xa"] > cur + 1e-4:
            mb.prism([(cur, z0), (o["xa"], z0), (o["xa"], z1), (cur, z1)], y0, y1, mat)
        if o["za"] > z0 + 1e-4:
            mb.prism([(o["xa"], z0), (o["xb"], z0), (o["xb"], o["za"]), (o["xa"], o["za"])], y0, y1, mat)
        arc = arch_points(o["xa"], o["xb"], o["zs"], o.get("kind", "flat"))
        top = max(p[1] for p in arc)
        if top < z1 - 1e-4:
            poly = arc + [(o["xb"], z1), (o["xa"], z1)]
            mb.prism(poly, y0, y1, mat)
        cur = o["xb"]
    if cur < x1 - 1e-4:
        mb.prism([(cur, z0), (x1, z0), (x1, z1), (cur, z1)], y0, y1, mat)


def figure(mb, base, h, robe="M_Statue", head=None, arms=True, pose=0.0):
    """Simplified standing statue / figurine (robe cone, torso, head)."""
    x, y, z = base
    head = head or robe
    mb.cyl((x, y, z), h * 0.16, h * 0.62, robe, segs=10, r_top=h * 0.09)
    mb.cyl((x, y, z + h * 0.62), h * 0.09, h * 0.18, robe, segs=10, r_top=h * 0.07)
    mb.sphere((x, y, z + h * 0.88), h * 0.075, head, segs=10, rings=6)
    if arms:
        mb.rod((x - h * 0.08, y, z + h * 0.76), (x - h * 0.17, y - h * 0.05 - pose, z + h * 0.5), h * 0.035, robe, segs=6)
        mb.rod((x + h * 0.08, y, z + h * 0.76), (x + h * 0.15, y - h * 0.1, z + h * 0.62 + pose), h * 0.035, robe, segs=6)


def spire(mb, cx, cy, z0, r, h, mat="M_Slate", segs=8, ball="M_Gold"):
    mb.cyl((cx, cy, z0), r, h, mat, segs=segs, r_top=0.0, smooth=False)
    if ball:
        mb.sphere((cx, cy, z0 + h + r * 0.12), r * 0.12 + 0.05, ball, segs=8, rings=5)
        mb.rod((cx, cy, z0 + h), (cx, cy, z0 + h + r * 0.4 + 0.4), 0.03, "M_Iron", segs=4)


# ----------------------------------------------------------------------------- scene / export
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def new_asset(name, category):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "PLAIN_AXES"
    root["asset_category"] = category
    col.objects.link(root)
    return root, col


def marker(name, loc, parent, col, rot_z=0.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 0.5
    e.location = loc
    e.rotation_euler = (0, 0, rot_z)
    col.objects.link(e)
    e.parent = parent
    return e


def point_light(name, loc, parent, col, energy=60.0, color=(1.0, 0.62, 0.3), radius=0.1, distance=12.0):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    try:
        ld.use_custom_distance = True
        ld.cutoff_distance = distance
    except AttributeError:
        pass
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    col.objects.link(ob)
    ob.parent = parent
    return ob


def set_origin(ob, pivot_world):
    """Move object origin to pivot (mesh stays where it is)."""
    pv = Vector(pivot_world)
    ob.data.transform(Matrix.Translation(-pv))
    ob.location = ob.location + pv


def colbox(mb_col, mn, mx):
    mb_col.box(mn, mx, "M_Trim")


def auto_collision(root, col, shrink=0.0):
    """Box collider from the bounds of all visible meshes of an asset."""
    pts = []
    for o in descendants(root):
        if o.type == "MESH" and not o.name.endswith("-colonly"):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts) + shrink, min(p.y for p in pts) + shrink, max(0.0, min(p.z for p in pts))))
    mx = Vector((max(p.x for p in pts) - shrink, max(p.y for p in pts) - shrink, max(p.z for p in pts)))
    mc = MB()
    mc.box(mn, mx, "M_Trim")
    return finish_collision(mc, root.name, root, col)


def finish_collision(mb_col, name, root, col):
    if not mb_col.faces:
        return None
    ob = mb_col.build(name + "-colonly", root, col)
    ob.display_type = "WIRE"
    ob.hide_render = True
    return ob


def descendants(ob):
    out = [ob]
    for c in ob.children:
        out += descendants(c)
    return out


GODOT_LIGHT_SCALE = 1.0 / 30.0   # 70 W torch in Blender -> energy 2.3 in Godot (RAW export)


def finally_restore(renames, light_e):
    for o, old in reversed(renames):
        o.name = old
    for ld, e in light_e:
        ld.energy = e


def export_asset(root, out_dir, extra_kw=None):
    """Export one asset hierarchy to glTF (separate .gltf/.bin, textures shared in assets/textures)."""
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    vl = bpy.context.view_layer
    for c in vl.layer_collection.children:
        c.exclude = c.name != root.users_collection[0].name
    for o in descendants(root):
        o.hide_set(False)
        o.select_set(True)
    vl.objects.active = root
    # 1) clean names: Blender suffixes duplicates (MARK_door.001); give this asset the base names
    import re
    renames = []
    for o in descendants(root):
        m = re.match(r"^(.*)\.\d{3}$", o.name)
        if m:
            base = m.group(1)
            other = bpy.data.objects.get(base)
            if other is not None and other is not o:
                tmp = "__tmp_" + base
                renames.append((other, other.name))
                other.name = tmp
            renames.append((o, o.name))
            o.name = base
    # 2) lights: Blender watts look right in EEVEE previews; Godot wants energy ~1-5
    light_e = []
    for o in descendants(root):
        if o.type == "LIGHT":
            light_e.append((o.data, o.data.energy))
            o.data.energy = o.data.energy * GODOT_LIGHT_SCALE
    path = os.path.join(out_dir, root.name + ".gltf")
    tex_rel = os.path.relpath(os.path.join(PROJECT, "assets", "textures"), out_dir).replace("\\", "/")
    kw = dict(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir=tex_rel,
              use_selection=True, export_lights=True, export_apply=True, export_yup=True,
              export_extras=True, export_import_convert_lighting_mode="RAW")
    kw.update(extra_kw or {})
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as e:
        print("gltf kw issue", e)
        kw.pop("export_extras", None)
        kw.pop("export_import_convert_lighting_mode", None)
        bpy.ops.export_scene.gltf(**kw)
    finally_restore(renames, light_e)
    for c in vl.layer_collection.children:
        c.exclude = False
    print("EXPORTED", path)
    return path
