"""UI art for Task 5: parchment / iron-frame textures (numpy) and 3D-rendered item icons (EEVEE).

blender -b --factory-startup -P make_ui_assets.py
Outputs: assets/ui/*.png, assets/ui/icons/*.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402
import lib_char  # noqa: E402,F401  (registers character materials)
import lib_tex as T  # noqa: E402
from lib_geo import MB  # noqa: E402

UI = os.path.join(G.PROJECT, "assets", "ui")
ICONS = os.path.join(UI, "icons")
PI = math.pi


def save_rgba(path, rgba):
    h, w = rgba.shape[:2]
    img = bpy.data.images.new("tmp", w, h, alpha=True)
    img.pixels.foreach_set(np.clip(rgba[::-1], 0, 1).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("UI", os.path.basename(path))


# ============================================================================= 2D textures
def parchment(size=512, seed=7):
    f = T.fbm(size, 3, 6, seed, 0.55)
    stains = T.smoothstep(0.62, 0.8, T.fbm(size, 5, 5, seed + 1))
    fib = T.value_noise(size, 160, seed + 2, 40)
    alb = T.colorize(f, ["#a8875a", "#c4a574", "#d6bc8c", "#e2cc9e"])
    alb *= (0.95 + 0.08 * fib)[..., None]
    alb = T.lerp(alb, alb * np.array([0.78, 0.66, 0.5]), stains[..., None] * 0.6)
    return np.dstack([alb, np.ones((size, size))])


def iron_frame(size=192, border=34, seed=11, inner=None):
    """9-slice frame: dark wood border with iron edge and rivets; transparent centre unless `inner`."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.minimum(np.minimum(xs, ys), np.minimum(size - 1 - xs, size - 1 - ys))
    wood = T.colorize(T.fbm(size, 4, 5, seed, 0.5, cells_y=1), ["#1e140d", "#2e2016", "#3e2c1e"])
    iron = T.colorize(T.fbm(size, 16, 3, seed + 1), ["#2a2a2c", "#45464a", "#5e6066"])
    a = np.zeros((size, size))
    rgb = np.zeros((size, size, 3))
    edge_out = d < 5
    edge_in = (d >= border - 6) & (d < border)
    body = d < border
    rgb[body] = wood[body]
    rgb[edge_out | edge_in] = iron[edge_out | edge_in]
    hi = (d >= 1) & (d < 2.5)
    rgb[hi] = rgb[hi] * 1.5
    a[body] = 1.0
    for cx, cy in ((border / 2, border / 2), (size - border / 2, border / 2), (border / 2, size - border / 2),
                   (size - border / 2, size - border / 2)):
        r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        m = r < 8.5
        rgb[m] = iron[m] * (1.4 - r[m][..., None] / 12)
        # corner ornament: gold leaf ring
        ring = (r > 10) & (r < 12.5) & body
        rgb[ring] = np.array([0.72, 0.55, 0.22])
    if inner is not None:
        cen = ~body
        rgb[cen] = inner[cen]
        a[cen] = 1.0
    return np.dstack([rgb, a])


def bar_fill(color, w=256, h=24, seed=3):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.array(color)
    shade = 0.65 + 0.55 * np.sin(np.clip(ys / (h - 1), 0, 1) * PI)
    n = T.fbm(256, 32, 3, seed)[:h, :w]
    rgb = base[None, None, :] * shade[..., None] * (0.9 + 0.2 * n[..., None])
    return np.dstack([rgb, np.ones((h, w))])


def disc_daynight(size=256):
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2
    r = np.sqrt(xs ** 2 + ys ** 2)
    a = (r < 0.98).astype(np.float32)
    day = T.colorize(T.fbm(size, 4, 3, 5), ["#5aa0d8", "#8cc4ec"])
    night = T.colorize(T.fbm(size, 4, 3, 6), ["#0c1430", "#1a2850"])
    rgb = np.where((xs < 0)[..., None], day, night)
    sun = np.sqrt((xs + 0.45) ** 2 + ys ** 2) < 0.24
    rgb = np.where(sun[..., None], np.array([1.0, 0.82, 0.3]), rgb)
    for k in range(12):
        ang = 2 * PI * k / 12
        ray = T._seg_dist(xs, ys, (-0.45 + 0.28 * math.cos(ang), 0.28 * math.sin(ang)),
                          (-0.45 + 0.4 * math.cos(ang), 0.4 * math.sin(ang))) < 0.03
        rgb = np.where((ray & (xs < 0))[..., None], np.array([1.0, 0.75, 0.25]), rgb)
    moon = (np.sqrt((xs - 0.45) ** 2 + ys ** 2) < 0.24) & ~(np.sqrt((xs - 0.55) ** 2 + (ys + 0.06) ** 2) < 0.21)
    rgb = np.where(moon[..., None], np.array([0.92, 0.9, 0.78]), rgb)
    rng = np.random.default_rng(3)
    for _ in range(18):
        sx, sy = rng.uniform(0.05, 0.9), rng.uniform(-0.8, 0.8)
        st = np.sqrt((xs - sx) ** 2 + (ys - sy) ** 2) < 0.018
        rgb = np.where((st & (xs > 0) & ~moon)[..., None], np.array([1, 1, 0.9]), rgb)
    rim = (r > 0.9) & (r < 0.98)
    rgb = np.where(rim[..., None], np.array([0.7, 0.53, 0.2]), rgb)
    return np.dstack([rgb, a])


def heart(size=64):
    ys, xs = (np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5) * 2.4
    ys = -ys
    m = (xs ** 2 + (ys - np.sqrt(np.abs(xs)) * 0.8) ** 2) < 0.9
    rgb = np.zeros((size, size, 3)) + np.array([0.75, 0.08, 0.06])
    rgb *= (0.7 + 0.5 * (ys[..., None] + 1) / 2)
    return np.dstack([rgb, m.astype(np.float32)])


def stamina_icon(size=64):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    pts = [(0.58, 0.05), (0.2, 0.55), (0.46, 0.55), (0.36, 0.95), (0.8, 0.4), (0.53, 0.4), (0.7, 0.05)]
    m = np.zeros((size, size), bool)
    # point-in-polygon (even-odd)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cond = ((y0 > ys) != (y1 > ys)) & (xs < (x1 - x0) * (ys - y0) / (y1 - y0 + 1e-9) + x0)
        m ^= cond
    rgb = np.zeros((size, size, 3)) + np.array([0.95, 0.72, 0.15])
    return np.dstack([rgb, m.astype(np.float32)])


def vignette(w=512, h=288, color=(0.35, 0.0, 0.0)):
    ys, xs = (np.mgrid[0:h, 0:w].astype(np.float32))
    nx, ny = (xs / w - 0.5) * 2, (ys / h - 0.5) * 2
    r = np.sqrt(nx ** 2 + ny ** 2)
    a = np.clip((r - 0.35) / 0.9, 0, 1) ** 1.5
    rgb = np.zeros((h, w, 3)) + np.array(color)
    return np.dstack([rgb, a])


def make_2d():
    os.makedirs(UI, exist_ok=True)
    p = parchment()
    save_rgba(os.path.join(UI, "parchment.png"), p)
    save_rgba(os.path.join(UI, "frame_iron.png"), iron_frame())
    save_rgba(os.path.join(UI, "panel_parchment.png"), iron_frame(inner=parchment(192, 9)[..., :3]))
    slot_inner = T.colorize(T.fbm(96, 4, 4, 13), ["#1a140f", "#2a2119"])
    save_rgba(os.path.join(UI, "slot.png"), iron_frame(96, 12, 13, inner=slot_inner))
    save_rgba(os.path.join(UI, "bar_health.png"), bar_fill((0.72, 0.07, 0.05)))
    save_rgba(os.path.join(UI, "bar_stamina.png"), bar_fill((0.86, 0.66, 0.12), seed=4))
    save_rgba(os.path.join(UI, "bar_back.png"), bar_fill((0.12, 0.1, 0.09), seed=5))
    save_rgba(os.path.join(UI, "daynight.png"), disc_daynight())
    save_rgba(os.path.join(UI, "heart.png"), heart())
    save_rgba(os.path.join(UI, "stamina.png"), stamina_icon())
    save_rgba(os.path.join(UI, "vignette_red.png"), vignette())
    btn = parchment(256, 21)[:64, :, :]
    btn[..., :3] *= 0.9
    save_rgba(os.path.join(UI, "button.png"), btn)
    hover = btn.copy()
    hover[..., :3] = T.lerp(hover[..., :3], np.array([0.55, 0.08, 0.06]), 0.75)
    save_rgba(os.path.join(UI, "button_hover.png"), hover)


# ============================================================================= 3D icons
def icon_scene():
    G.reset_scene()
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 128
    try:
        sc.eevee.taa_render_samples = 32
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    w = bpy.data.worlds.new("w")
    sc.world = w
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.6, 0.55, 0.5, 1)
    bg.inputs["Strength"].default_value = 0.8
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(40), math.radians(-20), math.radians(30))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.location = (0, -5, 0)
    cam.rotation_euler = (PI / 2, 0, 0)
    return cam


def render_icon(name, build, scale=1.0, rot=(0.0, 0.0, 0.0)):
    for o in list(bpy.data.objects):
        if o.type == "MESH":
            bpy.data.objects.remove(o)
    mb = MB()
    build(mb)
    ob = mb.build("icon_" + name)
    ob.rotation_euler = rot
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2
    ob.location = -c
    cam = bpy.context.scene.camera
    cam.data.ortho_scale = max(mx.x - mn.x, mx.z - mn.z) * 1.18 / scale
    bpy.context.scene.render.filepath = os.path.join(ICONS, name + ".png")
    bpy.ops.render.render(write_still=True)


def flask(mb, mat):
    mb.lathe([(0.05, 0.0), (0.2, 0.04), (0.26, 0.2), (0.22, 0.38), (0.08, 0.48), (0.06, 0.62), (0.075, 0.66)], "M_Glass_icon",
             segs=20)
    mb.lathe([(0.04, 0.02), (0.18, 0.05), (0.235, 0.2), (0.2, 0.33), (0.12, 0.4)], mat, segs=20)
    mb.cyl((0, 0, 0.6), 0.06, 0.12, "M_WoodLight", segs=10)


def make_icons():
    os.makedirs(ICONS, exist_ok=True)
    G.MATS["M_Glass_icon"] = (None, 0, 0.05, 0.0, {"color": (0.75, 0.82, 0.85)})
    G.MATS["M_PotRed"] = (None, 0, 0.2, 0.0, {"color": (0.7, 0.05, 0.05), "emit_color": (0.8, 0.05, 0.05), "strength": 0.6})
    G.MATS["M_PotBlue"] = (None, 0, 0.2, 0.0, {"color": (0.08, 0.2, 0.75), "emit_color": (0.1, 0.25, 0.9), "strength": 0.6})
    G.MATS["M_PotGreen"] = (None, 0, 0.2, 0.0, {"color": (0.15, 0.65, 0.12), "emit_color": (0.2, 0.8, 0.15), "strength": 0.6})
    icon_scene()
    m = G.get_mat("M_Glass_icon")
    next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Alpha"].default_value = 0.3
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    for nm, mat in (("potion_health", "M_PotRed"), ("potion_stamina", "M_PotBlue"), ("potion_antidote", "M_PotGreen")):
        render_icon(nm, lambda mb, mat=mat: flask(mb, mat))
    import build_characters as BC
    for lvl, blade in ((1, "M_Steel"), (2, "M_Steel"), (3, "M_Brass"), (4, "M_Gold")):
        def sword(mb, lvl=lvl, blade=blade):
            BC.sword_mesh(mb, 0.95 + 0.04 * lvl, blade, "M_LeatherC" if lvl < 3 else "M_ClothRed", "M_Iron" if lvl < 2 else "M_Brass")
        render_icon(f"sword_{lvl}", sword, rot=(0, math.radians(-45), 0))

    def shield(mb):
        with mb.at(rot_x=PI / 2):
            mb.cyl((0, 0, -0.015), 0.33, 0.03, "M_WoodDark", segs=24, smooth=False)
            mb.face([(0.32 * math.cos(2 * PI * k / 24), 0.32 * math.sin(2 * PI * k / 24), 0.017) for k in range(24)],
                    "M_Tabard", uv="fit")
    render_icon("shield", shield)

    def helmet(mb):
        mb.sphere((0, 0, 0), (0.2, 0.2, 0.2), "M_Steel", segs=20, rings=10, z_cut=0.0)
        lib_char.loft(mb, [Vector((0, 0, 0.02)), Vector((0, 0, 0.0))], [(0.33, 0.33), (0.34, 0.34)], "M_Steel", segs=24)
    render_icon("helmet", helmet, rot=(math.radians(15), 0, 0))

    def coif(mb):
        lib_char.loft(mb, [Vector((0, 0, 0)), Vector((0, 0, 0.3)), Vector((0, 0, 0.42))], [(0.3, 0.2), (0.2, 0.15), (0.1, 0.1)],
                      "M_Chainmail", segs=18)
    render_icon("chainmail", coif)

    def gloves(mb):
        for x in (-0.12, 0.12):
            mb.sphere((x, 0, 0), (0.08, 0.05, 0.12), "M_LeatherC", segs=12, rings=8)
            lib_char.loft(mb, [Vector((x, 0, -0.1)), Vector((x, 0, -0.25))], [0.07, 0.085], "M_LeatherC", segs=10)
    render_icon("gloves", gloves)

    def bread(mb):
        mb.sphere((0, 0, 0), (0.3, 0.16, 0.13), "M_Bread", segs=16, rings=8, noise=0.04, seed=2)
    render_icon("bread", bread, rot=(0.3, 0, 0.4))

    def meat(mb):
        mb.sphere((0, 0, 0), (0.25, 0.15, 0.12), "M_Meat", segs=14, rings=8, noise=0.08, seed=3)
        mb.rod((0.2, 0, 0), (0.38, 0, 0.05), 0.03, "M_Bone", segs=6)
    render_icon("meat", meat, rot=(0.3, 0, 0.3))

    def coins(mb):
        for i in range(5):
            mb.cyl((0.02 * (i % 2), 0, i * 0.035), 0.16, 0.03, "M_Gold", segs=20, smooth=False)
        mb.cyl((0.28, 0.0, 0), 0.16, 0.03, "M_Gold", segs=20, smooth=False)
    render_icon("gold", coins, rot=(0.5, 0, 0))

    def herb(mb):
        for k in range(5):
            a = k * 0.6 - 1.2
            lib_char.loft(mb, [Vector((0, 0, 0)), Vector((0.25 * math.sin(a), 0, 0.3 + 0.05 * math.cos(a)))], [(0.04, 0.01), (0.005, 0.005)],
                          "M_Cabbage", segs=6)
            mb.sphere((0.25 * math.sin(a), 0, 0.32), (0.07, 0.015, 0.1), "M_Cabbage", segs=8, rings=5)
    render_icon("herb", herb)

    def mushroom(mb):
        for x, s in ((-0.12, 1.0), (0.13, 0.8)):
            mb.cyl((x, 0, 0), 0.05 * s, 0.25 * s, "M_Linen", segs=10)
            mb.sphere((x, 0, 0.25 * s), (0.14 * s, 0.14 * s, 0.08 * s), "M_Pumpkin", segs=14, rings=7, z_cut=0.25 * s - 0.01)
    render_icon("mushroom", mushroom, rot=(0.25, 0, 0))

    def shard(mb):
        mb.sphere((0, 0, 0), (0.25, 0.18, 0.2), "M_Clay", segs=8, rings=5, noise=0.3, seed=5, smooth=False)
    render_icon("clay_shard", shard)

    def bone_dust(mb):
        mb.sphere((0, 0, 0), (0.3, 0.3, 0.12), "M_Bone", segs=14, rings=7, noise=0.15, seed=6, z_cut=0.0)
        mb.rod((-0.2, 0, 0.08), (0.2, 0.05, 0.15), 0.03, "M_Bone", segs=6)
    render_icon("bone_dust", bone_dust, rot=(0.6, 0, 0))

    def scroll(mb):
        with mb.at(rot_y=PI / 2):
            mb.cyl((0, 0, -0.3), 0.08, 0.6, "M_Linen", segs=14)
        mb.sphere((0, -0.08, 0), (0.05, 0.02, 0.05), "M_ClothRed", segs=10, rings=6)
    render_icon("scroll", scroll, rot=(0.3, 0, 0.5))

    def ring(mb):
        with mb.at(rot_x=1.2):
            mb.torus(0.2, 0.04, "M_Gold", segs=24, tsegs=8)
        mb.sphere((0, -0.05, 0.22), 0.06, "M_VialPurple", segs=10, rings=6)
    render_icon("ring", ring)

    def vial(mb):
        mb.lathe([(0.04, 0.0), (0.09, 0.05), (0.09, 0.3), (0.04, 0.36), (0.045, 0.42)], "M_Glass_icon", segs=14)
        mb.lathe([(0.03, 0.01), (0.08, 0.05), (0.08, 0.22)], "M_VialGreen", segs=14)
    render_icon("quicksilver", vial)

    def key(mb):
        with mb.at(rot_x=PI / 2):
            mb.torus(0.1, 0.025, "M_Iron", segs=16, tsegs=6)
        mb.rod((0.1, 0, 0), (0.45, 0, 0), 0.025, "M_Iron", segs=6)
        mb.box((0.36, -0.02, -0.1), (0.4, 0.02, 0.0), "M_Iron")
        mb.box((0.42, -0.02, -0.08), (0.45, 0.02, 0.0), "M_Iron")
    render_icon("key", key)
    make_quest_icons()


def make_quest_icons(only=None):
    """Hero weapons (same builders as the WEAPON_* meshes on vaclav.gltf) and quest items."""
    os.makedirs(ICONS, exist_ok=True)
    G.MATS["M_WaxRed"] = (None, 0, 0.35, 0.0, {"color": (0.55, 0.04, 0.03)})
    G.MATS["M_BlackIron"] = (None, 0, 0.45, 0.9, {"color": (0.06, 0.06, 0.07)})
    G.MATS["M_PaintBlue"] = (None, 0, 0.7, 0.0, {"color": (0.15, 0.3, 0.6)})
    if bpy.context.scene.camera is None:
        icon_scene()
    import build_characters as BC
    diag = (0, math.radians(-45), 0)
    jobs = {
        "w_sword": (lambda mb: BC.longsword(mb, 0.98), diag),
        "w_longsword": (lambda mb: BC.bastard_sword(mb), diag),
        "w_axe": (lambda mb: BC.war_axe(mb), (0, math.radians(-40), 0)),
        "w_greatsword": (lambda mb: BC.greatsword(mb), diag),
        "w_vysehrad": (lambda mb: BC.vysehrad_blade(mb), diag),
    }

    def ledger(mb):
        mb.box((-0.22, -0.06, -0.3), (0.22, 0.06, 0.3), "M_Linen")
        mb.box((-0.235, -0.075, -0.315), (0.235, -0.06, 0.315), "M_LeatherDark")
        mb.box((-0.235, 0.06, -0.315), (0.235, 0.075, 0.315), "M_LeatherDark")
        mb.box((-0.25, -0.075, -0.315), (-0.22, 0.075, 0.315), "M_LeatherDark")
        mb.box((0.18, -0.09, -0.04), (0.26, -0.07, 0.04), "M_Brass")
        mb.sphere((0, -0.08, 0), (0.07, 0.015, 0.07), "M_BlackIron", segs=12, rings=4)
    jobs["ledger"] = (ledger, (0.25, 0, 0.35))

    def sun_seal(mb):
        with mb.at(rot_x=PI / 2):
            mb.cyl((0, 0, -0.04), 0.28, 0.08, "M_BlackIron", segs=28)
            for k in range(12):
                a = 2 * PI * k / 12
                mb.prism([(0.1 * math.cos(a - 0.18), 0.1 * math.sin(a - 0.18)), (0.24 * math.cos(a), 0.24 * math.sin(a)),
                          (0.1 * math.cos(a + 0.18), 0.1 * math.sin(a + 0.18))], 0.04, 0.055, "M_Gold", plane="xy")
            mb.cyl((0, 0, 0.04), 0.09, 0.02, "M_Gold", segs=20)
        with mb.at((0, 0, 0.29), rot_x=PI / 2):
            mb.torus(0.06, 0.018, "M_Iron", segs=14, tsegs=6)
    jobs["sun_seal"] = (sun_seal, (0.15, 0, 0))

    def cloth_bale(mb):
        with mb.at(rot_y=PI / 2):
            mb.cyl((0, 0, -0.34), 0.17, 0.68, "M_ClothGreen", segs=20)
            mb.cyl((0, 0, -0.35), 0.06, 0.7, "M_WoodLight", segs=10)
        for x in (-0.2, 0.2):                       # rope bands round the roll
            with mb.at((x, 0, 0), rot_y=PI / 2):
                mb.cyl((0, 0, -0.02), 0.178, 0.04, "M_Rope", segs=20, cap=False)
    jobs["cloth_bale"] = (cloth_bale, (0.3, 0, 0.4))

    def cask(mb):
        mb.lathe([(0.17, 0.0), (0.22, 0.12), (0.235, 0.25), (0.22, 0.38), (0.17, 0.5)], "M_WoodLight", segs=20)
        for z, r in ((0.04, 0.185), (0.15, 0.228), (0.35, 0.228), (0.46, 0.185)):
            mb.cyl((0, 0, z - 0.012), r + 0.006, 0.024, "M_Iron", segs=20, cap=False)
        mb.rod((0, -0.2, 0.25), (0, -0.28, 0.25), 0.025, "M_WoodDark", segs=8)
    jobs["cask"] = (cask, (0.35, 0, 0.5))

    def letter(mb):
        mb.box((-0.3, -0.01, -0.2), (0.3, 0.01, 0.2), "M_Linen")
        mb.face([(-0.3, -0.012, 0.2), (0.3, -0.012, 0.2), (0.0, -0.012, -0.02)], "M_Linen")
        with mb.at((0, -0.02, -0.02), rot_x=PI / 2):
            mb.cyl((0, 0, -0.012), 0.07, 0.024, "M_WaxRed", segs=16)
    jobs["letter"] = (letter, (0.2, 0, 0.15))

    def toy_horse(mb):
        mb.box((-0.2, -0.07, 0.1), (0.2, 0.07, 0.24), "M_WoodLight")
        for x in (-0.15, 0.15):
            for y in (-0.05, 0.05):
                mb.box((x - 0.025, y - 0.02, -0.08), (x + 0.025, y + 0.02, 0.11), "M_WoodLight")
        mb.box((0.15, -0.05, 0.2), (0.23, 0.05, 0.38), "M_WoodLight")
        mb.box((0.17, -0.055, 0.32), (0.33, 0.055, 0.4), "M_WoodLight")
        mb.box((0.08, -0.02, 0.24), (0.2, 0.02, 0.4), "M_PaintBlue")
        mb.rod((-0.2, 0, 0.2), (-0.3, 0, 0.05), 0.02, "M_Rope", segs=6)
        for x in (-0.25, 0.25):
            with mb.at((x * 0.8, 0, -0.1), rot_x=PI / 2):
                mb.cyl((0, 0, -0.1), 0.05, 0.2, "M_WoodDark", segs=10)
    jobs["toy_horse"] = (toy_horse, (0.0, 0, 0.5))

    def bread_basket(mb):
        mb.lathe([(0.2, 0.0), (0.28, 0.08), (0.3, 0.2)], "M_Burlap", segs=20, cap_top=False)
        for k, (x, y) in enumerate(((-0.08, 0.0), (0.1, 0.04), (0.0, -0.1))):
            mb.sphere((x, y, 0.22), (0.12, 0.08, 0.07), "M_Bread", segs=12, rings=6, noise=0.05, seed=k)
        mb.rod((-0.28, 0, 0.2), (0.28, 0, 0.2), 0.015, "M_WoodLight", segs=6)
        with mb.at((0, 0, 0.2), rot_x=PI / 2):
            mb.torus(0.27, 0.014, "M_WoodLight", segs=20, tsegs=4)
    jobs["bread_basket"] = (bread_basket, (0.5, 0, 0.3))

    def iron_key(mb):
        with mb.at(rot_x=PI / 2):
            mb.torus(0.12, 0.03, "M_BlackIron", segs=16, tsegs=6)
        mb.rod((0.12, 0, 0), (0.5, 0, 0), 0.03, "M_BlackIron", segs=6)
        mb.box((0.4, -0.025, -0.14), (0.45, 0.025, 0.0), "M_Brass")
        mb.box((0.47, -0.025, -0.1), (0.5, 0.025, 0.0), "M_Brass")
    jobs["armoury_key"] = (iron_key, (0, 0, 0))
    for name, (fn, rot) in jobs.items():
        if only and name not in only:
            continue
        render_icon(name, fn, rot=rot)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--quest-icons" in argv:        # only the weapon / quest item icons
        icon_scene()
        make_quest_icons()
    else:
        make_2d()
        make_icons()
    print("DONE ui")
